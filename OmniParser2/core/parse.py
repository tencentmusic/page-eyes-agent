#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/12/25 19:46
import gc
import threading
from dataclasses import dataclass
from typing import Literal

import numpy as np
import torch
from PIL import Image
from paddleocr import PaddleOCR
from paddlex.inference.pipelines.ocr.result import OCRResult

from core.handler import BoxesHandler
from model.icon_captioner import IconCaptioner
from model.icon_detector import IconDetector
from model.overlay_detector import OverlayDetector, OVERLAY_CLASS_NAMES
from schemas.omni import OCRParams, IconDetectParams, IconCaptionParams, OverlayDetectParams
from util.context import context_var
from util.image import ImageUtil
from . import Element


@dataclass
class ParsedResult:
    elements: list[Element]
    ocr_elements: list[Element]
    icon_elements: list[Element]
    overlay_elements: list[Element]

threading_lock = threading.Lock()

@dataclass
class OmniParser:
    image: Image.Image  # 要解析的图片
    ocr: PaddleOCR
    ocr_params: OCRParams
    icon_detector: IconDetector
    icon_detect_params: IconDetectParams
    icon_captioner: IconCaptioner
    icon_caption_params: IconCaptionParams
    overlay_detector: OverlayDetector
    overlay_detect_params: OverlayDetectParams
    overlap_iou_threshold: float
    device: Literal['cuda', 'cpu']

    def ocr_predict(self) -> OCRResult:
        img_ndarray = np.asarray(self.image)
        params = self.ocr_params.model_dump(exclude_none=True)
        with threading_lock:
            return self.ocr.predict(img_ndarray, **params)[0]

    def icon_detect_predict(self) -> tuple[torch.Tensor, torch.Tensor]:
        params = self.icon_detect_params.model_dump(exclude_none=True)
        return self.icon_detector.predict(self.image, **params)

    def icon_caption_predict(self, images: list[Image.Image]) -> list[str]:
        params = self.icon_caption_params.model_dump(exclude_none=True)
        return self.icon_captioner.predict(images, **params)

    def overlay_detect_predict(self) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        params = self.overlay_detect_params.model_dump(exclude_none=True)
        return self.overlay_detector.predict(self.image, **params)

    # @profile  # 逐行统计内存消耗
    def parse(self) -> ParsedResult:
        """Parse the image and return structured output."""
        context = context_var.get()
        with context.timer_recorder.timer('ocr识别'):
            ocr_result = self.ocr_predict()
        ocr_boxes: np.ndarray[np.ndarray[np.int16]] = ocr_result.get('rec_boxes')
        ocr_texts: list[str] = ocr_result.get('rec_texts')
        ocr_scores: list[float] = ocr_result.get('rec_scores')
        # 目的 快速释放内存
        # gc.collect()释放内存给Python内存池，不保证还给操作系统
        # 操作系统回收发生在Python进程结束或内存压力大时
        del ocr_result
        gc.collect()

        w, h = self.image.size
        ocr_elements = []
        icon_elements = []

        if ocr_boxes.shape[0] > 0:
            # 少量数据直接放在 CPU 中计算
            # TODO 验证放 GPU 计算性能对比 torch.tensor(ocr_boxes, device='cuda')
            ocr_bboxes = torch.tensor(ocr_boxes) / torch.Tensor([w, h, w, h])
            ocr_bboxes = ocr_bboxes.tolist()  # Tensors are automatically moved to the CPU first if necessary

            ocr_elements = [
                Element(
                    type='text',
                    bbox=bbox,
                    score=score,
                    interactivity=False,
                    content=text,
                    source='box_ocr_content_ocr'
                )
                for bbox, text, score in zip(ocr_bboxes, ocr_texts, ocr_scores)
            ]

        with context.timer_recorder.timer('icon 目标检测'):
            icon_boxes, icon_scores = self.icon_detect_predict()
        if icon_boxes.shape[0] > 0:
            icon_bboxes = icon_boxes / torch.Tensor([w, h, w, h])
            icon_bboxes = icon_bboxes.tolist()
            icon_elements = [
                Element(
                    type='icon',
                    bbox=bbox,
                    interactivity=True,
                    content=None,
                    source='box_yolo_content_yolo',
                    score=score
                )
                for bbox, score in zip(icon_bboxes, icon_scores)
            ]
        del icon_boxes, icon_scores
        gc.collect()

        with context.timer_recorder.timer('移除重叠元素'):
            filtered_icon_elements, filtered_ocr_elements = BoxesHandler.remove_overlap(
                icon_elements,
                ocr_elements,
                iou_threshold=self.overlap_iou_threshold
            )
        with context.timer_recorder.timer('裁剪出icon元素'):
            cropped_images = ImageUtil.crop_images(self.image, [el.bbox for el in filtered_icon_elements])

        with context.timer_recorder.timer('icon元素识别'):
            icon_captions = self.icon_caption_predict(cropped_images)

        for el, caption in zip(filtered_icon_elements, icon_captions):
            el.content = caption

        del icon_captions
        gc.collect()

        with context.timer_recorder.timer('弹窗/加载中检测'):
            overlay_boxes, overlay_scores, overlay_classes = self.overlay_detect_predict()

        overlay_elements = []
        if overlay_boxes.shape[0] > 0:
            overlay_bboxes = overlay_boxes / torch.Tensor([w, h, w, h])
            overlay_bboxes = overlay_bboxes.tolist()
            overlay_elements = [
                Element(
                    type='overlay',
                    bbox=bbox,
                    interactivity=True,
                    content=OVERLAY_CLASS_NAMES.get(int(cls_idx), ''),
                    source='box_yolo_content_overlay',
                    score=float(score),
                )
                for bbox, score, cls_idx in zip(overlay_bboxes, overlay_scores, overlay_classes)
            ]
        del overlay_boxes, overlay_scores, overlay_classes
        gc.collect()

        merged_elements = filtered_icon_elements + filtered_ocr_elements + overlay_elements
        merged_elements = BoxesHandler.sort_elements_spatially(merged_elements)
        for i, el in enumerate(merged_elements):
            el.id = i

        return ParsedResult(
            elements=merged_elements,
            ocr_elements=ocr_elements,
            icon_elements=icon_elements,
            overlay_elements=overlay_elements,
        )
