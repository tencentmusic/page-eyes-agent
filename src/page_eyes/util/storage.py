#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/19 11:46
import asyncio
import hashlib
import imghdr
import io
import os
import time
from abc import ABC, abstractmethod
from io import BytesIO, StringIO
from typing import IO, Union, Any

from PIL import Image
from loguru import logger
from minio import Minio, S3Error
from qcloud_cos.cos_client import CosS3Client, CosConfig


class TinyImg:
    def __init__(self, fp: Union[IO, BytesIO, StringIO, Any]):
        self.fp = fp

    def is_image(self):
        location = self.fp.tell()
        h = self.fp.read(32)
        self.fp.seek(location)
        for tf in imghdr.tests:
            res = tf(h, self.fp)
            if res:
                return True
        return False

    def to_webp(self):
        """WebP 图像格式的最大分辨率为16383 x 16383"""
        location = self.fp.tell()
        try:
            img = Image.open(self.fp)
            max_size = max(img.size)
            if max_size > 16383:
                ratio = 16383 / max_size
                resize = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                logger.warning(f'图片宽高超过16383，将压缩图片大小：{img.size} -> {resize}')
                img = img.resize(resize)
            file = io.BytesIO()
            img.save(file, 'webp')
            self.fp.seek(location)
            file.seek(0)
            return file
        except Exception as e:
            error_file = f'{time.time()}_error_file.png'
            self.fp.seek(location)
            with open(error_file, 'wb') as f:
                # noinspection PyTypeChecker
                f.write(self.fp.read())
            logger.error(f'图片转换失败：错误文件 {error_file}')
            raise e


# 策略接口
class StorageStrategy(ABC):
    @abstractmethod
    def upload_file(self, file, prefix='', suffix='.png'):
        pass

    @abstractmethod
    async def async_upload_file(self, file, prefix='', suffix='.png'):
        pass

    @staticmethod
    def get_file_md5(file):
        file.seek(0)
        m = hashlib.md5()
        m.update(file.read())
        file.seek(0)
        return m.hexdigest()


# COS策略实现
class CosStrategy(StorageStrategy):
    def __init__(self, secret_id, secret_key, region, endpoint, bucket):
        _cos_config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Endpoint=endpoint)
        self._client = CosS3Client(_cos_config)
        self.bucket = bucket

    def upload_file(self, file, prefix='', suffix='.png'):
        file_md5 = self.get_file_md5(file)
        key = f'{prefix}{file_md5}{suffix}'

        try:
            if not self._client.object_exists(self.bucket, key):
                file = TinyImg(file).to_webp() if suffix == '.png' else file
                self._client.put_object(Bucket=self.bucket, Key=key, Body=file)
            cos_url = self._client.get_object_url(self.bucket, key)
            return cos_url
        except Exception as e:
            logger.error(f'上传文件失败：{e}')
            raise e

    async def async_upload_file(self, file, prefix='', suffix='.png'):
        return await asyncio.to_thread(self.upload_file, file, prefix=prefix, suffix=suffix)


# MinIO策略实现
class MinioStrategy(StorageStrategy):
    def __init__(self, access_key, secret_key, endpoint, bucket, region=None, secure=False):
        self._client = Minio(access_key=access_key, secret_key=secret_key, region=region, endpoint=endpoint,
                             secure=secure)
        self.endpoint = endpoint
        self.bucket = bucket
        self.protocol = 'https' if secure else 'http'

    def object_exists(self, key):
        try:
            self._client.stat_object(bucket_name=self.bucket, object_name=key)
            return True
        except S3Error as err:
            if err.code == "NoSuchKey":
                return False
            logger.error(f"MinIO服务异常: {err}")
        return False

    def upload_file(self, file, prefix='', suffix='.png'):
        file_md5 = self.get_file_md5(file)
        key = f'{prefix}{file_md5}{suffix}'

        try:
            if not self.object_exists(key):
                file = TinyImg(file).to_webp() if suffix == '.png' else file
                # 获取文件大小
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)
                self._client.put_object(bucket_name=self.bucket, object_name=key, data=file, length=file_size)

            return f"{self.protocol}://{self.endpoint}/{self.bucket}/{key}"
        except Exception as e:
            logger.error(f"上传文件失败: {e}")
            raise e

    async def async_upload_file(self, file, prefix='', suffix='.png'):
        return await asyncio.to_thread(self.upload_file, file, prefix=prefix, suffix=suffix)


# 主要的存储客户端类
class StorageClient:
    def __init__(self, strategy: StorageStrategy):
        self._strategy = strategy

    def __repr__(self):
        return f"StorageClient(strategy={self._strategy})"

    @classmethod
    def create_from_config(cls, cos_config, minio_config):
        """根据配置创建存储客户端"""
        # 优先使用COS，如果COS配置完整
        if cos_config.secret_id and cos_config.secret_key:
            strategy = CosStrategy(
                secret_id=cos_config.secret_id,
                secret_key=cos_config.secret_key,
                region=cos_config.region,
                endpoint=cos_config.endpoint,
                bucket=cos_config.bucket
            )
        # 如果COS配置不完整，使用MinIO
        elif minio_config.access_key and minio_config.secret_key:
            strategy = MinioStrategy(
                access_key=minio_config.access_key,
                secret_key=minio_config.secret_key,
                endpoint=minio_config.endpoint,
                bucket=minio_config.bucket,
                region=minio_config.region,
                secure=minio_config.secure
            )
        else:
            raise ValueError("未找到有效的存储配置，请检查COS或MinIO环境变量配置")

        return cls(strategy)

    def upload_file(self, file, prefix='', suffix='.png'):
        return self._strategy.upload_file(file, prefix, suffix)

    async def async_upload_file(self, file, prefix='', suffix='.png'):
        return await self._strategy.async_upload_file(file, prefix, suffix)
