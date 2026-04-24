#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: lancefayang
@created: 2025/6/23
@description: 异步版本的图像向量存储工具类
"""
import asyncio
import io
import json
import time
from datetime import datetime, timedelta
from typing import List, Optional

import clip
import numpy as np
import torch
from PIL import Image
from loguru import logger
from pymilvus import MilvusClient, DataType, AsyncMilvusClient

from util.context import context_var
from config import settings
from util.cos import download_file
from util.image_similarity import most_similar_images, SimilarImage


class AsyncImageVectorStorage:
    # CLIP模型支持的模型名称与向量维度的映射: model_name[str] -> vector_dim[int]
    model_dim_map: dict = {
        # VIT模型
        'ViT-B/32': 512,
        'ViT-B/16': 512,
        'ViT-L/14': 768,
        'ViT-L/14@336px': 768,
        # ResNet模型
        'RN50': 1024,
        'RN101': 512,
        'RN50x4': 640,
        'RN50x16': 768,
        'RN50x64': 1024,
    }

    def __init__(self, host='localhost', port='19530', collection_name='image_info_dynamic',
                 model=None, preprocess=None, vector_dim=None, device=None):
        """
        初始化异步图像向量存储系统

        注意：请使用 create_instance() classmethod 来创建实例，而不是直接调用构造函数

        Args:
            host: Milvus服务器地址
            port: Milvus服务器端口
            collection_name: 集合名称
            model: 已加载的CLIP模型
            preprocess: CLIP预处理函数
            vector_dim: 向量维度
            device: 设备类型
        """
        # 创建异步客户端连接
        self.client = AsyncMilvusClient(uri=f"http://{host}:{port}")

        # 保存参数
        self.host = host
        self.port = port

        # 集合名称
        self.collection_name = collection_name

        # CLIP模型相关
        self.model = model
        self.preprocess = preprocess
        self.vector_dim = vector_dim
        self.device = device

        if self.model:
            self.model.eval()

    @classmethod
    async def create_instance(cls, host='localhost', port='19530', collection_name='image_info_dynamic',
                              model_name='ViT-B/32'):
        """
        创建AsyncImageVectorStorage实例的工厂方法

        **注意**：更换模型时，若模型输出的维度发生变化，程序将重建collection，请注意备份数据避免数据丢失。

        Args:
            host: Milvus服务器地址
            port: Milvus服务器端口
            collection_name: 集合名称
            model_name: CLIP模型名称，可选: 'RN50', 'RN101', 'RN50x4', 'RN50x16', 'RN50x64',
                       'ViT-B/32', 'ViT-B/16', 'ViT-L/14', 'ViT-L/14@336px'，注意不同模型输出的向量维度可能不同

        Returns:
            AsyncImageVectorStorage实例
        """
        # 1. 初始化CLIP模型
        model, preprocess = clip.load(model_name, device=settings.device)

        # 获取特征向量维度
        vector_dim = cls.model_dim_map[model_name]

        # 2. 使用同步客户端完成初始化操作
        sync_client = MilvusClient(uri=f"http://{host}:{port}")

        try:
            # 初始化Collection
            await cls._init_collection_sync(sync_client, collection_name, vector_dim)

        finally:
            # 关闭同步客户端连接
            if hasattr(sync_client, 'close'):
                sync_client.close()

        # 3. 创建异步实例
        instance = cls(
            host=host,
            port=port,
            collection_name=collection_name,
            model=model,
            preprocess=preprocess,
            vector_dim=vector_dim,
            device=settings.device
        )

        # 4. 使用异步客户端加载Collection到内存
        await instance.client.load_collection(instance.collection_name)

        logger.info(f"异步图像向量存储实例创建成功，使用模型: {model_name}")
        return instance

    @staticmethod
    async def _init_collection_sync(sync_client: MilvusClient, collection_name: str, vector_dim: int):
        """使用同步客户端初始化Collection"""
        if sync_client.has_collection(collection_name):
            # 检查现有集合的schema
            collection_info = sync_client.describe_collection(collection_name)

            # 检查向量维度是否匹配（如更换模型，数据库将重建，请注意备份数据）
            vector_field = next((f for f in collection_info['fields'] if f['name'] == "vector"), None)
            if vector_field and vector_field.get('params', {}).get('dim') != vector_dim:
                logger.info(f"检测到向量维度不匹配，重建collection...")
                sync_client.drop_collection(collection_name)
                AsyncImageVectorStorage._create_collection_sync(sync_client, collection_name, vector_dim)
        else:
            AsyncImageVectorStorage._create_collection_sync(sync_client, collection_name, vector_dim)

    @staticmethod
    def _create_collection_sync(sync_client: MilvusClient, collection_name: str, vector_dim: int):
        """使用同步客户端创建新的Collection"""
        # 定义schema
        schema = sync_client.create_schema(
            auto_id=True,
            enable_dynamic_field=True,
        )

        # 添加字段
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)  # 主键，自增
        schema.add_field(  # 元素数据字段，使用ARRAY类型存储JSON字符串
            field_name="element_data",
            datatype=DataType.ARRAY,
            element_type=DataType.VARCHAR,
            max_capacity=1000,
            max_length=65535
        )
        schema.add_field(field_name="labeled_url", datatype=DataType.VARCHAR, max_length=1000)  # 标注后的图片URL
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=vector_dim)  # 图片转换的向量字段
        schema.add_field(field_name="timestamp", datatype=DataType.INT64)  # 时间戳
        schema.add_field(field_name="key", datatype=DataType.VARCHAR, max_length=100)  # 来源key

        # 创建索引参数
        index_params = sync_client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="IVF_FLAT",  # 使用IVF_FLAT索引
            metric_type="COSINE",  # 使用余弦相似度
            params={"nlist": 128}
        )
        # 为timestamp字段添加索引
        index_params.add_index(
            field_name="timestamp",
            index_type="STL_SORT"
        )

        # 创建集合
        sync_client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params
        )

        logger.info(f"成功创建集合: {collection_name}")

    def _image_to_vector(self, image: io.BytesIO) -> np.ndarray:
        """
        将图像转换为CLIP特征向量

        Args:
            image: io.BytesIO对象,包含图像数据

        Returns:
            归一化的特征向量
        """
        # 从BytesIO对象读取图像
        img = Image.open(image).convert('RGB')
        # 预处理图像
        image_input = self.preprocess(img).unsqueeze(0).to(self.device)

        # 提取特征
        with torch.no_grad():
            image_features = self.model.encode_image(image_input)
            # 立即移到CPU并转换为numpy
            image_features_np = image_features.cpu().numpy().flatten()

        # 关键修复：显式删除GPU tensor
        del image_input, image_features

        # 立即清理GPU显存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return image_features_np

    async def store(self,
                    image: io.BytesIO,
                    elements: List[dict],
                    labeled_url: str = "",
                    key: str = "",
                    check_exist: bool = True,
                    custom_timestamp: Optional[int] = None,
                    image_url: str = ""
                    ):
        """
        存储图片和元素信息

        Args:
            image: 图片（io.BytesIO对象，包含图像数据）
            elements: 元素信息列表，每个元素是一个字典
            labeled_url: 标注后的图片URL
            key: 来源key，用于区分服务调用来源
            check_exist: 是否按相似度阈值检查重复（true表示只存储不重复的图片）
            custom_timestamp: 自定义时间戳，如果为None则使用当前时间
            image_url: 原始图片URL

        """
        # 将截图转换为向量
        vector = self._image_to_vector(image)

        # 如果check_exist为True，则先查询是否已存在相似图片
        if check_exist:
            # 先查询是否已存在相似图片
            exists = await self.query(image, days_filter=1)
            if exists:
                logger.info("图片已存在，跳过存储")

        # 获取时间戳
        timestamp = custom_timestamp if custom_timestamp is not None else int(time.time())

        # 将元素列表转换为字符串列表（Milvus ARRAY字段要求）
        element_strings = [json.dumps(elem, ensure_ascii=False) for elem in elements]

        # 准备插入数据
        data = [{
            "element_data": element_strings,
            "labeled_url": labeled_url,
            "vector": vector.tolist(),
            "timestamp": timestamp,
            "key": key,
            "image_url": image_url,
        }]

        # 插入数据
        result = await self.client.insert(
            collection_name=self.collection_name,
            data=data
        )

        logger.info(f"成功存储解析结果，包含 {len(elements)} 个元素，"
                    f"标注后图片的URL: {labeled_url}，"
                    f"插入ID: {result['ids']}, "
                    f"时间戳: {timestamp}")

    async def query(self, image: io.BytesIO, days_filter: Optional[int] = None) -> Optional[dict]:
        """
        查询截图是否已存在，并返回元素信息和标注URL

        Args:
            image: 图片（io.BytesIO对象，包含图像数据）
            days_filter: 时间过滤，查询最近N天的数据，如果为None或为0则不过滤

        Returns:
            (是否存在, 包含元素信息和标注URL的字典或None)
            字典格式: {"elements": List[dict], "labeled_url": str}
        """
        context = context_var.get()

        # 将截图转换为向量
        vector = self._image_to_vector(image)

        # 构建时间过滤表达式
        filter_expr = None
        if days_filter is not None and days_filter > 0:
            # 计算N天前的时间戳
            days_ago = int((datetime.now() - timedelta(days=days_filter)).timestamp())
            filter_expr = f"timestamp >= {days_ago}"

        # 执行搜索
        results = await self.client.search(
            collection_name=self.collection_name,
            data=[vector.tolist()],
            limit=2,
            search_params={"metric_type": "COSINE", "params": {"nprobe": 10}},
            output_fields=["element_data", "labeled_url", "timestamp", "image_url"],
            filter=filter_expr
        )

        # 检查结果
        if len(results[0]) > 0:
            distance = results[0][0]['distance']
            logger.info(f"最高向量余弦相似度: {distance}")

            if distance >= settings.milvus_config.threshold:
                similarities = [item for item in results[0] if item['entity'].get('image_url')]
                if not similarities:
                    logger.warning("向量查询结果中未找到含原始图片的数据")
                    return None
                downloaded_images: list[bytes] = await asyncio.gather(
                    *[download_file(item['entity']['image_url']) for item in similarities]
                )

                query_image = Image.open(image)
                images = [Image.open(io.BytesIO(img)) for img in downloaded_images]
                similar_results: list[SimilarImage] = (
                    await asyncio.to_thread(most_similar_images, query_image, images)
                )
                logger.info(f'图片相似度对比结果: {[item.model_dump() for item in similar_results]}')

                most_similarity = similar_results[0]
                entity = similarities[most_similarity.corpus_id]['entity']
                logger.info(f"对比图片: {await context.image_upload_task}")
                logger.info(f"相似图片: {entity['image_url']}")

                if most_similarity.score >= settings.milvus_config.similarity_threshold:
                    # 找到相似图片
                    logger.info(f"图片匹配成功: 相似度 {most_similarity.score}")
                    element_strings = entity['element_data']
                    # 将字符串列表转换回字典列表
                    elements = [json.loads(s) for s in element_strings]

                    # 清理临时变量
                    del query_image, images, downloaded_images, similar_results

                    return {**entity, "elements": elements}
                else:
                    logger.info(
                        f"图片匹配失败: 相似度 {most_similarity.score} < 阈值 {settings.milvus_config.similarity_threshold}")

                # 清理临时变量
                del query_image, images, downloaded_images, similar_results

        # 未找到相似图片
        return None

    async def _delete_all(self):
        """删除所有数据（谨慎使用）"""
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                filter="id >= 0"
            )
            logger.info("已删除所有数据")
        except Exception as e:
            logger.error(f"删除数据失败: {e}")

    async def close(self):
        """关闭连接"""
        try:
            await self.client.close()
            logger.info("异步连接已关闭")
        except Exception as e:
            logger.error(f"关闭连接失败: {e}")

    async def __aenter__(self):
        """支持异步上下文管理器"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """支持异步上下文管理器"""
        await self.close()
