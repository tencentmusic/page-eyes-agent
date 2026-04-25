#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: lancefayang
@created: 2025/01/05
"""
import numpy as np
import supervision as sv
import torch
from supervision import Detections
from supervision.draw.base import ImageType
from torchvision.ops import box_iou, box_area


class CustomLabelAnnotator(sv.LabelAnnotator):
    """
    继承 supervision 的 LabelAnnotator，实现：
    1. 避免标签与检测框重叠（加权评分，小框优先保护）
    2. 避免标签之间重叠
    """

    def annotate(self,
                 scene: ImageType,
                 detections: Detections,
                 labels: list[str] | None = None,
                 custom_color_lookup: np.ndarray | None = None
                 ) -> ImageType:
        """重写 annotate 方法，增强标签位置布局适配"""
        # 保存 detections 供 _adjust_labels_in_frame
        setattr(self, '_detections', detections)
        return super().annotate(scene, detections, labels, custom_color_lookup)

    def _adjust_labels_in_frame(self, resolution_wh, labels, label_properties):
        """在父类基础上，智能调整标签位置避免重叠"""
        assert hasattr(self, '_detections') and isinstance(self._detections, Detections)
        detections: Detections = getattr(self, '_detections')
        if len(detections) == 0:
            return super()._adjust_labels_in_frame(resolution_wh, labels, label_properties)

        boxes = torch.tensor(detections.xyxy, dtype=torch.float32)
        areas = box_area(boxes)
        adjusted = label_properties.copy()
        placed_labels = None

        for i, (bbox, props) in enumerate(zip(detections.xyxy, label_properties)):
            label_w, label_h = props[2] - props[0], props[3] - props[1]
            best_pos = self._find_best_position(
                bbox, label_w, label_h, resolution_wh, i, boxes, areas, placed_labels
            )
            adjusted[i, :4] = best_pos

            # 记录已放置标签
            label_box = torch.tensor([best_pos], dtype=torch.float32)
            placed_labels = torch.cat([placed_labels, label_box]) if placed_labels is not None else label_box

        return super()._adjust_labels_in_frame(resolution_wh, labels, adjusted)

    def _find_best_position(self, bbox, label_w, label_h, resolution_wh, idx, boxes, areas, placed_labels):
        """四方向尝试，返回重叠最小的位置 [x1, y1, x2, y2]"""
        x1, y1, x2, y2 = bbox
        pad = self.text_padding

        # 按优先级尝试四个方向
        candidates = [
            (x1, y1 - label_h - pad),  # top
            (x2 + pad, y1),  # right
            (x1, y2 + pad),  # bottom
            (x1 - label_w - pad, y1),  # left
        ]

        best, best_score = None, float('inf')
        for nx1, ny1 in candidates:
            nx2, ny2 = nx1 + label_w, ny1 + label_h

            # 边界检查
            if nx1 < 0 or nx2 > resolution_wh[0] or ny1 < 0 or ny2 > resolution_wh[1]:
                continue

            label_box = torch.tensor([[nx1, ny1, nx2, ny2]], dtype=torch.float32)

            # 检查与已放置标签重叠
            if placed_labels is not None and box_iou(label_box, placed_labels).max() > 0:
                continue

            # 计算与检测框的加权重叠分数
            iou = box_iou(label_box, boxes)[0]
            iou[idx] = 0  # 排除自身
            score = (iou / areas).sum().item()

            if score == 0:
                return [nx1, ny1, nx2, ny2]
            if score < best_score:
                best, best_score = [nx1, ny1, nx2, ny2], score

        return best if best else [x1, y1 - label_h - pad, x1 + label_w, y1 - pad]
