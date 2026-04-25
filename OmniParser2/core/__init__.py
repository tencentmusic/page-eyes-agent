#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/12/25 20:32
from pydantic import BaseModel, Field


class Element(BaseModel):
    id: int | None = None
    type: str
    bbox: list[float]
    interactivity: bool
    content: str | None
    score: float = 0
    source: str
    left_elem_ids: list[int] = Field(default_factory=list)
    top_elem_ids: list[int] = Field(default_factory=list)
    right_elem_ids: list[int] = Field(default_factory=list)
    bottom_elem_ids: list[int] = Field(default_factory=list)

