# -*- coding: utf-8 -*-
# @author : leenjiang
# @since   : 2025/3/9

from typing import Optional, Tuple, Union

import torch
from PIL import Image
from loguru import logger
from ultralytics import YOLO

from config import settings


OVERLAY_CLASS_NAMES: dict[int, str] = {
    0: '页面加载中',
    1: '弹窗',
    2: '弹窗',
    3: '弹窗关闭按钮',
}


class OverlayDetector:
    """
    弹窗/加载中 YOLO 检测器封装类

    识别图像中的弹窗（dialog/bottom_sheet）、弹窗关闭按钮（close）
    以及页面加载中（loading）等覆盖层元素。
    """

    def __init__(self):
        self.model_file = settings.overlay_yolo_config.model_file
        self.model = self._load_model()

    def _load_model(self) -> YOLO:
        """
        加载 YOLO 模型。

        Returns:
            YOLO: 加载好的 YOLO 模型实例。

        Raises:
            FileNotFoundError: 如果模型文件不存在。
        """
        if not self.model_file.exists():
            raise FileNotFoundError(
                f'Overlay YOLO model file not found: {self.model_file}，'
                f'请将训练好的 best.pt 放置到该路径。'
            )
        logger.info(f'loading overlay detector model from {self.model_file}...')
        return YOLO(self.model_file)

    def predict(
            self,
            image: Union[Image.Image, str],
            conf: Optional[float] = None,
            iou: Optional[float] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        执行弹窗/加载中检测。

        Args:
            image: 输入图像，可以是 PIL Image 对象或文件路径。
            conf: 置信度阈值，默认使用配置值。
            iou: NMS IoU 阈值，默认使用配置值。

        Returns:
            Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
                - boxes: 检测框坐标 (xyxy)，已移动到 CPU。
                - scores: 置信度分数，已移动到 CPU。
                - classes: 类别索引，已移动到 CPU。
        """
        conf = conf if conf is not None else settings.overlay_yolo_config.conf
        iou = iou if iou is not None else settings.overlay_yolo_config.iou

        try:
            results = self.model.predict(
                source=image,
                conf=conf,
                iou=iou,
                verbose=False,
            )

            if not results:
                logger.warning('overlay YOLO 推理结果为空')
                return torch.empty(0, 4), torch.empty(0), torch.empty(0, dtype=torch.long)

            result = results[0]
            boxes = result.boxes.xyxy.cpu()
            scores = result.boxes.conf.cpu()
            classes = result.boxes.cls.cpu().long()

            return boxes, scores, classes

        except Exception as e:
            logger.error(f'overlay YOLO 推理出现异常: {e}')
            return torch.empty(0, 4), torch.empty(0), torch.empty(0, dtype=torch.long)
