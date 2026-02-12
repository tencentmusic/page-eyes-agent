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
from dotenv import load_dotenv
from .util.storage import StorageClient

load_dotenv()


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


class BrowserConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='browser_', extra='ignore')

    headless: Optional[bool] = True
    simulate_device: Optional[Literal['iPhone 15', 'iPhone 15 Pro', 'iPhone 15 Pro Max', 'iPhone 6'] | str] = None


class OmniParserConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='omni_', extra='ignore')

    base_url: Optional[str] = 'http://127.0.0.1:8000'
    key: Optional[str] = ''


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='agent_', extra='ignore')

    model: Optional[str] = 'openai:deepseek-chat'
    model_settings: ModelSettings = ModelSettings(max_tokens=20000, temperature=0.2)

    browser: BrowserConfig = BrowserConfig()

    omni_parser: OmniParserConfig = OmniParserConfig()

    storage_client: StorageClient = StorageClient.create_from_config(CosConfig(), MinioConfig())

    debug: Optional[bool] = False


default_settings = Settings()
