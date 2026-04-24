# -*- coding: utf-8 -*-
# @author : leenjiang
# @since   : 2025/12/18 19:35


import gc
from typing import Dict
from typing import List


import torch
from PIL import Image
from huggingface_hub import snapshot_download
from loguru import logger
from peft import PeftModel
from transformers import AutoModelForCausalLM
from transformers import AutoProcessor

from config import settings


class IconCaptioner:
    """
    图标描述生成器封装类。
    如果开启自训练模型开关，使用自训练Florence-2模型；否则使用microsoft/Florence-2-base-ft模型
    负责模型加载、图像预处理、Batch推理
    """

    DEFAULT_PROMPT = "<CAPTION>"

    def __init__(self):
        """
        初始化 IconCaptioner
        """
        self.model_repo_id = settings.caption_config.hf_repo_id
        self.model_dir = settings.caption_config.model_dir
        self.use_ft_model = settings.caption_config.use_ft_model

        self.device = settings.device

        self.max_new_tokens = settings.caption_config.max_new_tokens

        self.model = None
        self.processor = None
        self._load_model()

    def _load_model(self) -> None:
        """加载 Florence2 模型"""

        if not (self.model_dir / 'model.safetensors').exists():
            logger.warning(f"Florence-2-base-ft model files not found from {self.model_dir}, "
                           f"downloading from HuggingFace...")
            snapshot_download(
                repo_id=settings.caption_config.hf_repo_id,
                allow_patterns=['*.json', '*.safetensors', '*.py'],
                local_dir=self.model_dir
            )

        logger.info(f"loading Florence-2-base-ft model...")

        # 指定eager模式
        attn_implementation = "eager"

        base_model = AutoModelForCausalLM.from_pretrained(
            self.model_dir,
            dtype=settings.torch_dtype,
            attn_implementation=attn_implementation,
            trust_remote_code=True,
        ).to(self.device)

        if self.use_ft_model:
            # 加载微调后的模型 (LoRA)
            ft_model_dir = settings.caption_config.ft_model_dir
            logger.info(f"loading LoRA Adapter: {ft_model_dir}...")
            self.model = PeftModel.from_pretrained(
                base_model,
                ft_model_dir,
                trust_remote_code=True
            )
            self.model = self.model.to(dtype=settings.torch_dtype)
            self.processor = AutoProcessor.from_pretrained(
                ft_model_dir,
                trust_remote_code=True
            )
        else:
            logger.info(f"using official model: {self.model_repo_id} revision: {settings.caption_config.hf_repo_revision}")
            self.model = base_model
            self.processor = AutoProcessor.from_pretrained(
                self.model_dir,
                trust_remote_code=True
            )

    def predict(
            self,
            images: List[Image.Image],
            prompt: str = DEFAULT_PROMPT,
            batch_size: int = settings.caption_config.batch_size
    ) -> List[str]:
        """
        生成图像描述。

        Args:
            images (List[Image.Image]): PIL 图像列表。
            prompt (str): 提示词。
            batch_size (int): 批处理大小。

        Returns:
            List[str]: 生成的描述文本列表。
        """
        if not images:
            return []

        generated_texts = []

        try:
            for i in range(0, len(images), batch_size):
                batch_images = images[i:i + batch_size]
                batch_prompts = [prompt] * len(batch_images)

                # 预处理
                inputs = self._prepare_inputs(batch_images, batch_prompts)

                # 推理
                batch_texts = self._inference(inputs)
                generated_texts.extend(batch_texts)

                # 显式释放引用，但不强制GC
                del inputs

        except Exception as e:
            logger.error(f"Florence2模型生成Caption时出现异常: {e}")
            # 发生异常时再清理显存
            self._clear_gpu_memory()
            return []

        return generated_texts

    def _prepare_inputs(self, images: List[Image.Image], prompts: List[str]) -> Dict[str, torch.Tensor]:
        """准备模型输入"""
        inputs = self.processor(images=images, text=prompts, return_tensors="pt")

        # 只对 pixel_values 转换为 float16，input_ids 保持 int64
        return {
            k: (
                v.to(device=self.device, dtype=settings.torch_dtype, non_blocking=True)
                if k == "pixel_values"
                else v.to(device=self.device, non_blocking=True)
            )
            for k, v in inputs.items()
        }

    @torch.inference_mode()
    def _inference(self, inputs: Dict[str, torch.Tensor]) -> List[str]:
        """执行模型推理"""
        generated_ids = self.model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=self.max_new_tokens,
            num_beams=1,
            do_sample=False,
            use_cache=False,
            early_stopping=False
        )

        # 立即移到 CPU 并解码
        generated_ids_cpu = generated_ids.cpu()
        del generated_ids

        generated_text = self.processor.batch_decode(
            generated_ids_cpu,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True  # 自动清理空格
        )
        return generated_text

    @staticmethod
    def _clear_gpu_memory():
        """清理 GPU 显存"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()