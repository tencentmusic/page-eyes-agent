#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/12/25 20:13

from pydantic import BaseModel, Field

from config import settings
from util.timer import TimerRecorder


class OCRParams(BaseModel):
    text_det_thresh: float | None = Field(
        default=settings.ocr_config.text_det_thresh, description="文本检测二值化阈值")
    text_det_box_thresh: float | None = Field(
        default=settings.ocr_config.text_det_box_thresh, description="文本检测框阈值")
    text_det_limit_side_len: float | None = Field(
        default=settings.ocr_config.text_det_limit_side_len, description="文本检测限制边长")
    text_det_limit_type: str | None = Field(
        default=settings.ocr_config.text_det_limit_type, description="文本检测限制类型")
    text_det_unclip_ratio: float | None = Field(
        default=settings.ocr_config.text_det_unclip_ratio, description="文本检测unclip比例")
    text_rec_score_thresh: float | None = Field(
        default=settings.ocr_config.text_rec_score_thresh, description="文本识别得分阈值")


class IconDetectParams(BaseModel):
    conf: float = Field(default=settings.yolo_config.conf, description="置信度阈值")
    iou: float = Field(default=settings.yolo_config.iou, description="IoU 阈值")


class OverlayDetectParams(BaseModel):
    conf: float = Field(default=settings.overlay_yolo_config.conf, description="弹窗检测置信度阈值")
    iou: float = Field(default=settings.overlay_yolo_config.iou, description="弹窗检测 IoU 阈值")


class IconCaptionParams(BaseModel):
    batch_size: int = Field(default=settings.caption_config.batch_size, description="批处理大小")


class ImgCacheParams(BaseModel):
    store: bool = Field(default=True, description="是否存储处理结果")
    within_days: int = Field(default=1, description="获取缓存最近天数")


class ParsedResponse(BaseModel):
    parsed_content_list: list
    labeled_image_url: str
    image_url: str
    visualize: str | None = None
    timer: TimerRecorder | None = None
