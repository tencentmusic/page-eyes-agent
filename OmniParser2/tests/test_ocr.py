#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/12/22 15:35
from pathlib import Path

from paddlex.inference.common.result import BaseCVResult
from paddlex.inference.pipelines.ocr.result import OCRResult

from config import settings
from paddleocr import PaddleOCR
from loguru import logger

ocr = PaddleOCR(paddlex_config=settings.ocr_config)


def test_ocr():
    res: OCRResult = ocr.predict('./images/ocr_01.png')[0]
    logger.info(res.json)
    output = Path('./output/ocr_res_01.png')
    res.save_to_img(str(output))
    logger.info(output.resolve().as_uri())
