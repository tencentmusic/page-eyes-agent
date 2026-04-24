#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/17 20:19
import math
import os
from typing import Union, IO, List, Optional

import numpy as np
import torch
from PIL import Image, ImageOps
from loguru import logger
import cv2


StrOrBytesPath = Union[str, bytes, os.PathLike[str], os.PathLike[bytes]]


class ImageUtil:
    def __init__(self, fp: StrOrBytesPath | IO[bytes] | Image.Image):
        self.image = fp if isinstance(fp, Image.Image) else Image.open(fp)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.image.close()

    def is_loading_screen(
            self,
            dominance_threshold: float = 0.9,
            color_bits_to_reduce: int = 6,
            crop_padding: tuple[float, float, float, float] | None = None) -> bool:
        """
        通过分析图像像素的颜色分布来判断截图是否为加载中或空白页面。

        主要逻辑是：如果图像中绝大多数像素点是同一种或非常相似的颜色，那么我们认为它是一个加载中/空白页面。

        :param crop_padding: left, upper, right, and lower pixel ratios to crop from the image.
        :param dominance_threshold: 单一颜色占比的阈值，超过这个值则认为是加载页。默认为 0.95 (95%)。
        :param color_bits_to_reduce: 颜色通道的位数，用于合并相似颜色。值越小，颜色种类越少。
                                     例如，4 表示每个通道有 2^4=16 个色阶。默认为 4。
        :return: 如果判断为加载页面，返回 True；否则返回 False。
        """

        # 1. 降低颜色深度，将相似的颜色合并
        # posterize 会将每个颜色通道的位数减少到指定值
        # 这有助于处理因压缩或微小渐变导致的颜色差异
        if color_bits_to_reduce < 1 or color_bits_to_reduce > 8:
            raise ValueError("color_bits_to_reduce 必须在 1 到 8 之间")
        if crop_padding is None:
            if self.image.width > self.image.height:
                # 如果图像宽度大于高度，适用PC
                crop_padding = (0.12, 0.08, 0.02, 0)
            else:
                # 如果图像高度大于宽度，适用手机
                crop_padding = (0, 0.12, 0, 0.08)

        crop_box = (
            self.image.width * crop_padding[0],
            self.image.height * crop_padding[1],
            self.image.width - self.image.width * crop_padding[2],
            self.image.height - self.image.height * crop_padding[3]
        )

        # 用于debug
        # x1, y1, x2, y2 = crop_box
        # draw = ImageDraw.Draw(self.image)
        # draw.line([(x1, y1), (x2, y1)], fill='red', width=6)
        # draw.line([(x2, y1), (x2, y2)], fill='red', width=6)
        # draw.line([(x2, y2), (x1, y2)], fill='red', width=6)
        # draw.line([(x1, y2), (x1, y1)], fill='red', width=6)
        # self.image.show()

        image = self.image.crop(crop_box)
        image = ImageOps.posterize(image, color_bits_to_reduce)
        total_pixels = image.width * image.height

        # 2. 高效地获取所有像素的颜色及其数量
        # getcolors() 返回一个列表，每个元素是 (count, (r, g, b))
        colors = image.getcolors(maxcolors=total_pixels)

        # 3. 找到最主要的颜色
        # getcolors 返回的列表未按数量排序，因此需要手动排序
        colors.sort(key=lambda item: item[0], reverse=True)
        dominant_color_count, dominant_color_rgb = colors[0]

        # 4. 计算最主要颜色的占比
        dominance_ratio = dominant_color_count / total_pixels

        # 5. 判断占比是否超过阈值
        is_loading = dominance_ratio >= dominance_threshold

        logger.info(f"is loading: {is_loading}, dominance color: {dominant_color_rgb}  ratio: {dominance_ratio}")

        return is_loading

    @staticmethod
    def crop_images(
            image: Image.Image,
            bboxes: list[list[float]],
    ) -> list[Image.Image]:
        """
        根据边界框裁剪图像
        Args:
            image (Image.Image): 原始图像。
            bboxes (list[list[float]]): 边界框列表 [x1, y1, x2, y2] (相对坐标)。

        Returns:
            list[Image.Image]: 裁剪后的 PIL 图像列表。
        """
        w, h = image.size
        cropped_images = []
        for bbox in bboxes:
            x1, y1, x2, y2 = np.array(bbox, np.float16) * [w, h, w, h]
            # 整体外扩一点点，避免直接取整带来边缘缺失，同时边界检查，避免裁剪超出
            x1, y1 = int(x1), int(y1)
            x2, y2 = min(math.ceil(x2), w), min(math.ceil(y2), h)

            crop = image.crop((x1, y1, x2, y2))
            cropped_images.append(crop)
        return cropped_images

    @staticmethod
    def _enhance_image_contrast(
            image_np: np.ndarray,
            scale_factor: float = 2.0,
            clip_limit: float = 5.0
    ) -> np.ndarray:
        """图像对比度增强"""
        # 转灰度
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

        # 小图放大
        h, w = gray.shape[:2]
        if max(h, w) < 400:
            gray = cv2.resize(
                gray,
                (int(w * scale_factor), int(h * scale_factor)),
                interpolation=cv2.INTER_CUBIC
            )

        # CLAHE 增强
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(4, 4))
        gray = clahe.apply(gray)

        # 自适应阈值
        if np.std(gray) < 5:  # low_contrast_std
            gray = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY, 15, 10
            )

        return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
