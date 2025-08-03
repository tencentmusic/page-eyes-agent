#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/19 11:46
import asyncio
import hashlib
import imghdr
import io
import time
from io import BytesIO, StringIO
from typing import IO, Union, Any

from PIL import Image
from qcloud_cos.cos_client import CosS3Client, CosConfig

from loguru import logger


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


class CosClient:
    def __init__(self, secret_id, secret_key, region, endpoint, bucket):
        _cos_config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Endpoint=endpoint)
        self._client = CosS3Client(_cos_config)
        self.bucket = bucket

    @staticmethod
    def get_file_md5(file):
        location = file.tell()
        m = hashlib.md5()
        m.update(file.read())
        file.seek(location)
        return m.hexdigest()

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
