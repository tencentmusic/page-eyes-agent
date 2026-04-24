#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/15 17:28
from datetime import datetime

from fastapi import APIRouter, status

from util.response import Response

router = APIRouter()


@router.get("", summary="健康检查", status_code=status.HTTP_200_OK)
async def health_check():
    """健康检查"""
    return Response(data={"status": "ok", 'datetime': f'{datetime.now():%Y-%m-%d %T}'})
