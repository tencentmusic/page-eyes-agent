from asyncio.tasks import Task
from contextvars import ContextVar
from io import BytesIO
from typing import Optional

from PIL import Image
from pydantic import BaseModel, Field, ConfigDict

from util.timer import TimerRecorder

trace_id_var: ContextVar[str] = ContextVar('trace_id')
context_var: ContextVar[Optional['Context']] = ContextVar('context', default=None)


class Context(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    image: Image.Image = None
    image_upload_task: Task | None = None
    image_buffer: BytesIO | None = None
    qsize: int = 0
    timer_recorder: TimerRecorder = Field(default_factory=TimerRecorder, description='耗时记录器')
