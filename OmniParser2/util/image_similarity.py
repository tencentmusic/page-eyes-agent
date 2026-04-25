#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/11/21 16:47
from PIL.Image import Image
from pydantic import BaseModel, ConfigDict, Field
from similarities import ImageHashSimilarity


class SimilarImage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    corpus_id: int
    corpus_doc: Image = Field(exclude=True)
    score: float


def most_similar_images(query_image: Image, images: list[Image], top_n: int = 10) -> list[SimilarImage]:
    sim = ImageHashSimilarity(corpus=images, hash_function="average_hash", hash_size=128)
    result = sim.most_similar(query_image, topn=top_n)
    return [SimilarImage(**item) for item in result[0]]
