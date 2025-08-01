#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/24 12:18
from typing import Literal, Optional

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
load_dotenv(override=True)


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

    headless: Optional[bool] = True
    model: Optional[str] = 'openai:deepseek-v3'
    omni_base_url: Optional[str] = ''
    cos_base_url: Optional[str] = ''
    simulate_device: Optional[Literal['iPhone 15', 'iPhone 15 Pro', 'iPhone 15 Pro Max', 'iPhone 6'] | str] = None
    debug: Optional[bool] = False
    log_graph_node: Optional[bool] = False

    def copy_and_update(self, **kwargs):
        validated_settings = self.model_validate(kwargs)
        return self.model_copy(update=validated_settings.model_dump(exclude_none=True), deep=True)


global_settings = Settings()
