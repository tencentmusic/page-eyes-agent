#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/24 12:18
from typing import Literal, Optional

from loguru import logger
from pydantic import Field
from pydantic_ai.settings import ModelSettings
from pydantic_settings import BaseSettings, SettingsConfigDict

from .util.storage import StorageClient


class CosConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='cos_', extra='ignore')

    region: str = Field(default='')
    secret_id: str = Field(default='')
    secret_key: str = Field(default='')
    endpoint: str = Field(default='')
    bucket: str = Field(default='')


class MinioConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='minio_', extra='ignore')

    access_key: str = Field(default='')
    secret_key: str = Field(default='')
    endpoint: str = Field(default='')
    bucket: str = Field(default='')
    region: str = Field(default='')
    secure: bool = Field(default=False)


def create_storage_client():
    """创建存储客户端的工厂函数"""
    cos_config = CosConfig()
    minio_config = MinioConfig()
    return StorageClient.create_from_config(cos_config, minio_config)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='agent_', extra='ignore')

    headless: Optional[bool] = True
    model: Optional[str] = 'openai:deepseek-v3'
    omni_base_url: Optional[str] = ''
    omni_key: Optional[str] = ''
    storage_client: StorageClient = Field(default=create_storage_client())
    simulate_device: Optional[Literal['iPhone 15', 'iPhone 15 Pro', 'iPhone 15 Pro Max', 'iPhone 6'] | str] = None
    debug: Optional[bool] = False

    def copy_and_update(self, **kwargs):
        # TODO: 这里又会实例化一次 StorageClient，建议改成单例模式 @lancefayang
        validated_settings = self.model_validate(kwargs)
        try:
            logger.level('DETAIL', no=20) if validated_settings.debug else logger.level('DETAIL', no=10)
        except ValueError:
            pass
        # 不对 storage_client 进行深拷贝，而是重用原来的实例
        update_dict = validated_settings.model_dump(exclude_none=True)
        if 'storage_client' not in update_dict:
            update_dict['storage_client'] = self.storage_client
        return self.model_copy(update=update_dict, deep=False)


global_settings = Settings()

model_settings = ModelSettings(max_tokens=20000, temperature=0.0)
