#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/15 17:06
import logging
from pathlib import Path
from typing import Optional, Literal

import torch
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from torch import dtype

from util.storage import StorageClient

"""
优先级规则（从高到低）：
1. 代码中传入的参数（如 Settings(headless=False)）
2. 环境变量
3. .env 文件
4. 类属性默认值
"""
load_dotenv()

root_path: Path = Path(__file__).parent


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


class OCRConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='OCR_', extra='ignore')

    paddlex_config: str = str(root_path / 'OCR.yaml')  # OCR 默认配置

    # 图像边长限制：对输入图像的尺寸进行限制
    # 如果图像的最大边长超过 limit_side_len，则按比例缩小图像，确保图像最大边不超过指定值，默认 960
    text_det_limit_side_len: int = 960

    # 限制类型：min表示限制最小边，max表示限制最大边，默认 max
    text_det_limit_type: Literal['min', 'max'] = 'max'

    # 二值化阈值：用于文本区域的初步分割（0-1之间）
    # 值越小，检测越敏感，可能产生更多候选区域， 默认 0.3
    text_det_thresh: float = 0.6

    # 文本框阈值：过滤低置信度的文本框（0-1之间）
    # 值越大，过滤越严格，只保留高置信度的检测结果，默认 0.6
    text_det_box_thresh: float = 0.6

    # 文本框扩展比例：扩大检测框以包含完整文本
    # 1.5表示将检测框扩大1.5倍，确保不遗漏边缘文字， 默认 2.0
    text_det_unclip_ratio: float = 1.5

    # 文本识别批处理大小, 内存不足可配置环境变量
    text_recognition_batch_size: int = 6

    # 识别分数阈值：过滤低置信度的识别结果（0-1之间）
    # 0.0表示不过滤，保留所有识别结果
    text_rec_score_thresh: float = 0.7


class YoloConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='YOLO_', extra='ignore')

    model_dir: Path = root_path / 'model' / 'weights'
    model_file: Path = model_dir / 'icon_detect' / 'model.pt'

    hf_repo_id: str = 'microsoft/OmniParser-v2.0'
    hf_repo_revision: str = '6600256'  # 模型git版本
    hf_allow_patterns: str = 'icon_detect/*'

    conf: float = 0.05  # 置信度阈值，阈值越高，框越少，越准确, OmniParser为 0.05
    iou: float = 0.1  # IoU 阈值，阈值越高，框越多，越冗余, OmniParser为 0.1


class OverlayYoloConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='OVERLAY_YOLO_', extra='ignore')

    model_dir: Path = root_path / 'model' / 'weights'
    model_file: Path = model_dir / 'overlay_detect' / 'model.pt'

    conf: float = 0.6  # 置信度阈值，弹窗识别要求较高精度
    iou: float = 0.5  # IoU 阈值


class CaptionConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='CAPTION_', extra='ignore')

    hf_repo_id: str = 'microsoft/Florence-2-base-ft'
    hf_repo_revision: str = 'f6c1a25'  # 模型git版本

    model_dir: Path = root_path / 'model/weights/icon_caption'

    # 是否使用微调模型
    use_ft_model: bool = True
    ft_model_dir: Path = root_path / 'model/weights/icon_caption_finetune'

    batch_size: int = 4
    max_new_tokens: int = 20


class MilvusConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='MILVUS_', extra='ignore')

    enable: bool = True
    host: str = 'localhost'
    port: int = 19530
    threshold: float = 0.9999
    similarity_threshold: float = 0.95


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    root_path: Path = root_path
    openapi_url: Optional[str] = None  # 默认禁用 OpenAPI JSON 文件 (/openapi.json)、Swagger UI 和 ReDoc，规避安全风险
    log_level: str | int = logging.INFO
    max_concurrency: int = 4  # 最大并发数，限流用
    storage_client: StorageClient = StorageClient.create_from_config(CosConfig(), MinioConfig())
    storage_prefix: str = 'omni-parser/'

    milvus_config: MilvusConfig = MilvusConfig()

    ocr_config: OCRConfig = OCRConfig()
    yolo_config: YoloConfig = YoloConfig()
    overlay_yolo_config: OverlayYoloConfig = OverlayYoloConfig()
    caption_config: CaptionConfig = CaptionConfig()

    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
    torch_dtype: dtype = torch.float32 if device == 'cpu' else torch.float16

    overlap_iou_threshold: float = 0.9
    auto_reload: bool = False


settings = Settings()
