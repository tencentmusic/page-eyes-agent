#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/24 12:18
import logging
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

"""
优先级规则（从高到低）：
1. 代码中传入的参数（如 Settings(headless=False)）
2. 环境变量
3. .env 文件
4. 类属性默认值
"""
load_dotenv()


class CosConfig(BaseSettings):
    # todo: 暂时保留，后续看看是否需要
    model_config = SettingsConfigDict(env_file='.env', env_prefix='cos_', extra='ignore')

    region: str = Field(default='ap-guangzhou')
    secret_id: str = Field(default='')
    secret_key: str = Field(default='')
    endpoint: str = Field(default='cos-internal.ap-guangzhou.tencentcos.cn')
    bucket: str = Field(default='tme-dev-test-cos-1257943044')


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='agent_', extra='ignore')

    headless: bool = True
    model: str = 'openai:deepseek-v3'
    omni_base_url: str = 'http://21.6.91.201:8000'
    cos_base_url: str = 'http://uniqc.woa.com/api/tools/file-upload/'
    debug: bool = False


settings = Settings()
