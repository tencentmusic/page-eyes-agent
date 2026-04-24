# -*- coding: utf-8 -*-
# @author : leenjiang
# @since   : 2025/12/22 12:04

import pytest
import numpy as np
from PIL import Image

from config import settings
from model.icon_detector import IconDetector
from model.icon_captioner import IconCaptioner
from util.image import ImageUtil


@pytest.fixture(scope="session")
def icon_detector():
    return IconDetector()


@pytest.fixture(scope="session")
def icon_captioner():
    return IconCaptioner()


def _get_test_image(filename):
    image_path = settings.root_path / "tests" / "pics" / filename

    if image_path.exists():
        return image_path
    print(f"测试图片不存在: {filename}")
    return None


def test_yolo(icon_detector):
    """测试yolo模型"""
    img_path = _get_test_image("coins.png")
    if not img_path:
        pytest.skip("测试图片不存在, 跳过测试")

    image = Image.open(img_path).convert('RGB')
    boxes, scores = icon_detector.predict(image)

    assert boxes is not None
    assert scores is not None

    print(f"检查到 {len(boxes)} items")

    if len(boxes) > 0:
        # 保存裁剪后的小图到临时目录
        import shutil
        output_dir = settings.root_path / "tests" / "output" / "yolo_crops"
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        w, h = image.size
        boxes_norm = boxes.clone()
        boxes_norm[:, [0, 2]] /= w
        boxes_norm[:, [1, 3]] /= h

        cropped_images = ImageUtil.crop_images(image, boxes_norm.tolist())
        for i, crop_img in enumerate(cropped_images):
            crop_img.save(output_dir / f"crop_{i}.png")

        print(f"已保存 {len(cropped_images)} 张裁剪图片到 {output_dir}")


def test_florence2(icon_captioner):
    """测试florence2模型"""
    img_path = _get_test_image("battery.png")
    if not img_path:
        pytest.skip("测试图片不存在, 跳过测试")

    image = Image.open(img_path).convert('RGB')
    captions = icon_captioner.predict([image], batch_size=4)

    assert all(isinstance(c, str) for c in captions)

    print(f"Caption推理结果: {captions[0]}")


def test_icon_recognition(icon_detector, icon_captioner):
    """从图标框选到描述生成的完整流程"""
    img_path = _get_test_image("coins.png")
    # img_path = _get_test_image("single_element.png")

    if not img_path:
        pytest.skip("测试图片不存在, 跳过测试")

    image = Image.open(img_path).convert('RGB')
    boxes, scores = icon_detector.predict(image)

    assert boxes is not None
    assert scores is not None

    print(f"检查到 {len(boxes)} items.")

    if len(boxes) > 0:
        w, h = image.size
        boxes_norm = boxes.clone()
        boxes_norm[:, [0, 2]] /= w
        boxes_norm[:, [1, 3]] /= h

        cropped_images = ImageUtil.crop_images(image, boxes_norm.tolist())
        assert len(cropped_images) == len(boxes)

        captions = icon_captioner.predict(cropped_images, batch_size=4)

        assert len(captions) == len(cropped_images)
        assert all(isinstance(c, str) for c in captions)

        for i, (box, cap) in enumerate(zip(boxes, captions)):
            print(f"Item {i} [Box: {box.tolist()}]: {cap}")

    else:
        print("未检查到items. 跳过caption生成")

