# -*- coding: utf-8 -*-
# @author : leenjiang
# @since   : 2025/12/18 09:44
from pathlib import Path
from typing import List, Tuple, Union, Optional

import torch
from PIL import Image
from huggingface_hub import snapshot_download
from loguru import logger
from ultralytics import YOLO

from config import settings


class IconDetector:
    """
    YOLO 模型封装类，用于框选图像中的图标。
    负责模型的加载（支持自动下载）、推理以及显存管理。
    """

    def __init__(self):
        """
        初始化 IconDetector。
        """
        self.model_dir = settings.yolo_config.model_dir
        self.model_file = settings.yolo_config.model_file
        self.model = self._load_model()

    def _load_model(self) -> YOLO:
        """
        加载 YOLO 模型。如果本地不存在，尝试从 HuggingFace 下载。

        Returns:
            YOLO: 加载好的 YOLO 模型实例。

        Raises:
            FileNotFoundError: 如果模型文件无法找到且无法下载。
            RuntimeError: 如果模型加载失败。
        """
        # 检查本地文件是否存在
        if not self.model_file.exists():
            logger.warning(f"YOLO model file not found from {self.model_dir}, downloading from HuggingFace...")
            snapshot_download(
                repo_id=settings.yolo_config.hf_repo_id,
                allow_patterns=settings.yolo_config.hf_allow_patterns,
                local_dir=self.model_dir
            )

        # 加载模型
        logger.info(f"loading icon detector model...")
        return YOLO(self.model_file)

    def predict(
            self,
            image: Union[Image.Image, str],
            conf: Optional[float] = settings.yolo_config.conf,
            iou: Optional[float] = settings.yolo_config.iou
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        执行图标检测

        Args:
            image (Union[Image.Image, str]): 输入图像，可以是 PIL Image 对象或文件路径。
            conf (Optional[float]): 置信度阈值。默认使用配置值。
            iou (Optional[float]): NMS IOU 阈值。默认使用配置值。

        Returns:
            Tuple[torch.Tensor, torch.Tensor, List[str]]:
                - boxes: 检测框坐标 (xyxy)，已移动到 CPU。
                - conf: 置信度分数，已移动到 CPU。
        """

        try:
            # 实测发现不传imgsz效果更优，去除单独配置
            results = self.model.predict(
                source=image,
                conf=conf,
                iou=iou,
                verbose=False
            )

            if not results:
                logger.warning("YOLO推理结果为空")
                return torch.empty(0, 4), torch.empty(0)

            result = results[0]

            # 关键：立即将结果从 GPU 移到 CPU，避免显存累积
            # ultralytics 的 boxes.xyxy 和 boxes.conf 可能是 GPU tensor
            boxes = result.boxes.xyxy.cpu()
            scores = result.boxes.conf.cpu()

            return boxes, scores

        except Exception as e:
            logger.error(f"YOLO推理出现异常: {e}")
            return torch.empty(0, 4), torch.empty(0)
