#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/12/28 12:15

import numpy as np
import supervision as sv
from PIL.Image import Image
from rtree import index

from util.label_annotator import CustomLabelAnnotator
from . import Element


# TODO: torchvision 有很多现成的图像处理函数，后续优化可以考虑使用
class BoxesHandler:

    @staticmethod
    def box_area(box):
        """
        计算边界框的面积
        :param box: [x1, y1, x2, y2]
        :return: 面积
        """
        return (box[2] - box[0]) * (box[3] - box[1])

    @staticmethod
    def intersection_area(box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        return max(0, x2 - x1) * max(0, y2 - y1)

    @classmethod
    def calculate_iou(cls, box1, box2):
        """
        计算两个边界框的交并比(Intersection over Union)

        为什么要加 1e-6？
        这是一个数值稳定性技巧，主要目的是：
        1. 防止除零错误：在后续计算 intersection / union 时，如果 union = 0，会导致除零错误
        2. 避免浮点数精度问题：当两个框完全不重叠且面积极小时，可能出现浮点数精度问题
        3. 保证数值稳定性：1e-6 足够小，不会影响正常计算结果，但能避免边界情况
        Args:
            box1: 第一个边界框 [x1, y1, x2, y2]
            box2: 第二个边界框 [x1, y1, x2, y2]
            
        Returns:
            float: IoU值，取交并比、box1覆盖率、box2覆盖率三者的最大值
        """
        intersection = cls.intersection_area(box1, box2)
        union = cls.box_area(box1) + cls.box_area(box2) - intersection + 1e-6
        if cls.box_area(box1) > 0 and cls.box_area(box2) > 0:
            ratio1 = intersection / cls.box_area(box1)
            ratio2 = intersection / cls.box_area(box2)
        else:
            ratio1, ratio2 = 0, 0
        return max(intersection / union, ratio1, ratio2)

    @classmethod
    def is_inside(cls, box1, box2):
        """
        判断 box1 是否在 box2 内
        """
        intersection = cls.intersection_area(box1, box2)
        ratio = intersection / cls.box_area(box1)
        return ratio > 0.80

    @staticmethod
    def build_rtree_index(elements: list) -> index.Index | None:
        """
        构建 R-tree 索引
        """
        if not elements:
            return None
        idx = index.Index()
        for i, element in enumerate(elements):
            bbox = element.bbox
            idx.insert(i, bbox)
        return idx

    @classmethod
    def remove_overlap(
            cls,
            icon_elements: list[Element],
            ocr_elements: list[Element],
            iou_threshold: float
    ) -> tuple[list[Element], list[Element]]:
        """
        使用 R-tree 空间索引优化重叠检测，复杂度从 O(N²) 降到 O(N log N)

        icon_elements format: [{'type': 'icon', 'bbox':[x,y], 'interactivity':True, 'content':None }, ...]
        ocr_elements format: [{'type': 'text', 'bbox':[x,y], 'interactivity':False, 'content':str }, ...]
        """
        # 构建 R-tree 索引 - 为 icon boxes 建立索引
        icon_bbox_idx = cls.build_rtree_index(icon_elements)

        # 为 OCR boxes 也建立 R-tree 索引
        ocr_bbox_idx = cls.build_rtree_index(ocr_elements)

        # 使用 R-tree 快速查找重叠候选
        # 直接原地在 icon_elements, ocr_elements 中删除重叠的元素
        # 面积计算使用缓存，避免重复计算
        filtered_icon_elements = []
        filtered_ocr_elements = [*ocr_elements]
        for i, icon_element in enumerate(icon_elements):
            icon_bbox1 = icon_element.bbox
            is_valid_bbox = True

            # 只检查与 box1 可能重叠的 icon boxes 候选（空间查询）
            candidates = list(icon_bbox_idx.intersection(icon_bbox1))
            for j in candidates:
                if i == j:
                    continue
                icon_bbox2 = icon_elements[j].bbox
                # keep the smaller box
                if (cls.calculate_iou(icon_bbox1, icon_bbox2) > iou_threshold
                        and cls.box_area(icon_bbox1) > cls.box_area(icon_bbox2)):
                    is_valid_bbox = False
                    break

            if is_valid_bbox:
                if ocr_elements:
                    element_added = False
                    ocr_labels = ''

                    # 使用 R-tree 快速查找可能重叠的 OCR boxes
                    ocr_candidates = list(ocr_bbox_idx.intersection(icon_bbox1))

                    for j in ocr_candidates:
                        if not element_added:
                            ocr_element = ocr_elements[j]
                            ocr_bbox = ocr_element.bbox

                            if cls.is_inside(ocr_bbox, icon_bbox1):  # ocr inside icon
                                try:
                                    # TODO 为什么不是移除 icon box(拼接在一起是否影响点击小元素)，什么情况下异常？
                                    ocr_labels += ocr_element.content + ' '
                                    # TODO remove 复杂度是 O(N), 可以优化
                                    filtered_ocr_elements.remove(ocr_element)
                                except:
                                    continue
                            elif cls.is_inside(icon_bbox1, ocr_bbox):  # icon inside ocr
                                element_added = True
                                break

                    if not element_added:
                        if ocr_labels:
                            filtered_ocr_elements.append(
                                Element(
                                    type='icon',
                                    bbox=icon_element.bbox,
                                    interactivity=True,
                                    score=icon_element.score,
                                    content=ocr_labels.strip(),
                                    source='box_yolo_content_ocr')
                            )
                        else:
                            filtered_icon_elements.append(
                                Element(
                                    type='icon',
                                    bbox=icon_element.bbox,
                                    interactivity=True,
                                    score=icon_element.score,
                                    content=None,
                                    source='box_yolo_content_yolo'
                                )
                            )
                else:
                    filtered_icon_elements.append(icon_element)

        return filtered_icon_elements, filtered_ocr_elements

    @classmethod
    def sort_elements_spatially(cls, elements: list[Element]):
        """
        扫描线算法进行元素排序，并为每个元素添加空间关系信息

        Args:
            elements: 包含bbox信息的元素列表，每个元素应包含'bbox'字段
                     bbox格式为[x1, y1, x2, y2]（归一化坐标）

        Returns:
            排序后的元素列表，每个元素新增以下字段：
            - left_elem_ids: 同行左侧元素的id列表
            - top_elem_ids: 上行重叠元素的id列表
            - right_elem_ids: 同行右侧元素的id列表
            - bottom_elem_ids: 下行重叠元素的id列表
        """

        def has_vertical_overlap(elem1, elem2):
            """检查两个元素是否有垂直重叠"""
            return not (elem1['y2'] <= elem2['y1'] or elem2['y2'] <= elem1['y1'])

        def calculate_overlap_ratio(elem1, elem2):
            """计算两个元素的垂直重叠比例"""
            if not has_vertical_overlap(elem1, elem2):
                return 0.0

            overlap_start = max(elem1['y1'], elem2['y1'])
            overlap_end = min(elem1['y2'], elem2['y2'])
            overlap_height = overlap_end - overlap_start

            min_height = min(elem1['height'], elem2['height'])
            return overlap_height / min_height if min_height > 0 else 0.0

        def calculate_horizontal_overlap_ratio(elem1, elem2):
            """计算两个元素的水平重叠比例"""
            # 检查是否有水平重叠
            if elem1['x2'] <= elem2['x1'] or elem2['x2'] <= elem1['x1']:
                return 0.0

            overlap_start = max(elem1['x1'], elem2['x1'])
            overlap_end = min(elem1['x2'], elem2['x2'])
            overlap_width = overlap_end - overlap_start

            min_width = min(elem1['width'], elem2['width'])
            return overlap_width / min_width if min_width > 0 else 0.0

        def calculate_vertical_distance(elem1, elem2):
            """计算两个元素的垂直距离"""
            if has_vertical_overlap(elem1, elem2):
                return 0.0

            if elem1['y2'] <= elem2['y1']:
                return elem2['y1'] - elem1['y2']
            else:
                return elem1['y1'] - elem2['y2']

        def should_be_same_row(elem1, elem2):
            """判断两个元素是否应该在同一行"""
            # 1. 如果有显著的垂直重叠（>40%），则认为在同一行
            overlap_ratio = calculate_overlap_ratio(elem1, elem2)
            if overlap_ratio > 0.4:
                return True

            # 2. 如果垂直距离很小，且高度相近，则可能在同一行
            vertical_distance = calculate_vertical_distance(elem1, elem2)
            avg_height = (elem1['height'] + elem2['height']) / 2

            # 垂直距离小于平均高度的30%，且有一定重叠或距离很近
            if vertical_distance < avg_height * 0.3:
                # 进一步检查中心点距离
                center_distance = abs(elem1['y'] - elem2['y'])
                if center_distance < avg_height * 0.5:
                    return True

            # 3. 对于归一化坐标，使用绝对阈值作为兜底
            if overlap_ratio > 0.2 and vertical_distance < 0.015:
                return True

            return False

        # 开始排序
        if not elements:
            return elements

        # 计算每个元素的详细信息
        element_info = []
        for i, element in enumerate(elements):
            x1, y1, x2, y2 = element.bbox
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            height = y2 - y1
            width = x2 - x1
            element_info.append({
                'index': i,
                'element': element,
                'x': center_x,
                'y': center_y,
                'y1': y1,
                'y2': y2,
                'x1': x1,
                'x2': x2,
                'height': height,
                'width': width
            })

        # 按y坐标排序（先按顶部边界，再按中心点）
        element_info.sort(key=lambda x: (x['y1'], x['y']))

        # 使用改进的扫描线算法进行行分组
        rows = []
        processed = [False] * len(element_info)

        for i, current_elem in enumerate(element_info):
            if processed[i]:
                continue

            # 开始新行
            current_row = [current_elem]
            processed[i] = True

            # 使用扫描线思想：从当前元素开始，向下扫描寻找同行元素
            j = i + 1
            while j < len(element_info):
                if processed[j]:
                    j += 1
                    continue

                candidate = element_info[j]

                # 如果候选元素的顶部已经远离当前行的底部，停止扫描
                current_row_bottom = max(elem['y2'] for elem in current_row)
                if candidate['y1'] > current_row_bottom + 0.02:  # 归一化坐标下的合理阈值
                    break

                # 检查候选元素是否与当前行中的任何元素兼容
                can_join = any(should_be_same_row(row_elem, candidate) for row_elem in current_row)

                if can_join:
                    # 进一步验证：确保加入后不会破坏行的一致性
                    temp_row = current_row + [candidate]
                    row_is_consistent = True

                    # 检查新行中所有元素对是否都兼容
                    for k in range(len(temp_row)):
                        for l in range(k + 1, len(temp_row)):
                            if not should_be_same_row(temp_row[k], temp_row[l]):
                                # 如果不兼容，但有足够的重叠，仍然允许
                                overlap = calculate_overlap_ratio(temp_row[k], temp_row[l])
                                if overlap < 0.3:
                                    row_is_consistent = False
                                    break
                        if not row_is_consistent:
                            break

                    if row_is_consistent:
                        current_row.append(candidate)
                        processed[j] = True

                j += 1

            rows.append(current_row)

        # 按行的最顶部元素排序
        rows.sort(key=lambda row_elements: min(elem['y1'] for elem in row_elements))

        # 行内严格按x坐标排序（扫描线算法的本意）
        sorted_elements = []
        element_to_row_map = {}  # 记录每个元素属于哪一行

        for row_idx, row in enumerate(rows):
            row.sort(key=lambda elem: (elem['x1'], elem['x']))
            for elem_info in row:
                element_to_row_map[elem_info['index']] = row_idx
            sorted_elements.extend([info['element'] for info in row])

        # 为每个元素添加空间关系信息
        for i, element in enumerate(sorted_elements):
            # 找到当前元素在原始列表中的索引
            current_elem_info = None
            current_row_idx = None
            for elem_info in element_info:
                if elem_info['element'] is element:
                    current_elem_info = elem_info
                    current_row_idx = element_to_row_map[elem_info['index']]
                    break

            if current_elem_info is None:
                continue

            # 计算同行的左右元素
            current_row = rows[current_row_idx]
            for other_elem_info in current_row:
                if other_elem_info['index'] == current_elem_info['index']:
                    continue

                # 找到其他元素在sorted_elements中的索引
                other_elem_index = sorted_elements.index(other_elem_info['element'])

                # 左侧元素：x坐标更小, 越接近的越靠前
                if other_elem_info['x1'] < current_elem_info['x1']:
                    element.left_elem_ids.append(other_elem_index)
                # 右侧元素：x坐标更大
                elif other_elem_info['x1'] > current_elem_info['x1']:
                    element.right_elem_ids.append(other_elem_index)

            # 计算上下行的重叠元素（只考虑紧邻的相邻行）
            # 上一行（紧邻）
            if current_row_idx > 0:
                prev_row = rows[current_row_idx - 1]
                for other_elem_info in prev_row:
                    # 计算水平重叠率
                    h_overlap = calculate_horizontal_overlap_ratio(current_elem_info, other_elem_info)

                    if h_overlap >= 0.1:  # 重叠率>=10%
                        other_elem_index = sorted_elements.index(other_elem_info['element'])
                        element.top_elem_ids.append(other_elem_index)

            # 下一行（紧邻）
            if current_row_idx < len(rows) - 1:
                next_row = rows[current_row_idx + 1]
                for other_elem_info in next_row:
                    # 计算水平重叠率
                    h_overlap = calculate_horizontal_overlap_ratio(current_elem_info, other_elem_info)

                    if h_overlap >= 0.1:  # 重叠率>=10%
                        other_elem_index = sorted_elements.index(other_elem_info['element'])
                        element.bottom_elem_ids.append(other_elem_index)

            # 对ID列表进行排序，保持一致性
            element.left_elem_ids.sort(reverse=True)
            element.top_elem_ids.sort(reverse=True)
            element.right_elem_ids.sort()
            element.bottom_elem_ids.sort()

        return sorted_elements

    @classmethod
    def annotate(cls, image: Image, elements: list[Element], visualize=False) -> Image:
        image = image.copy()  # 避免修改原图
        if not elements:
            return image
        w, h = image.size
        class_map = {
            'box_yolo_content_yolo': 'i',
            'box_ocr_content_ocr': 'o',
            'box_yolo_content_ocr': 'io',
            'box_yolo_content_overlay': 'ov',
        }
        bboxes, classes, scores = zip(*[(el.bbox, class_map[el.source], el.score) for el in elements])
        xyxy = np.asarray(bboxes) * [w, h, w, h]
        class_id = np.asarray(classes)
        scores = np.asarray(scores)

        # noinspection PyTypeChecker
        detections = sv.Detections(xyxy=xyxy, class_id=class_id, confidence=scores)

        # 根据图像尺寸动态计算绘制参数
        ratio = max(image.size) / 3200
        draw_config = {
            'thickness': max(int(3 * ratio), 1),  # bbox 线条粗细
            'text_scale': 0.8 * ratio,  # 标签文字大小
            'text_thickness': max(int(2 * ratio), 1),  # 标签文字粗细
            'text_padding': max(int(3 * ratio), 1),  # 标签内边距
        }

        box_annotator = sv.BoxAnnotator(
            color_lookup=sv.ColorLookup.INDEX,
            thickness=draw_config['thickness']
        )
        label_annotator = CustomLabelAnnotator(
            color_lookup=sv.ColorLookup.INDEX,
            smart_position=True,
            text_scale=draw_config['text_scale'],
            text_thickness=draw_config['text_thickness'],
            text_padding=draw_config['text_padding']
        )

        annotated_image = box_annotator.annotate(
            scene=image, detections=detections)

        labels = [
            f"{idx}-{class_name}-{confidence:.2f}"
            for idx, class_name, confidence
            in zip(range(len(detections.xyxy)), detections.class_id, detections.confidence)
        ] if visualize else [str(idx) for idx in range(len(detections.xyxy))]
        annotated_image = label_annotator.annotate(
            scene=annotated_image, detections=detections, labels=labels)
        return annotated_image
