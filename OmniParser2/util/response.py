#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/18 15:00
from typing import Optional, Generic, TypeVar


from pydantic import BaseModel, computed_field

from util.context import trace_id_var

T = TypeVar('T')


class Response(BaseModel, Generic[T]):
    code: int = 0
    data: Optional[T] = None

    @computed_field
    @property
    def trace_id(self) -> str:
        return trace_id_var.get()


class ErrorResponse(Response, Generic[T]):
    code: int = 500
    data: Optional[T] = None
    msg: str



