import asyncio
import sys

from loguru import logger
from page_eyes.agent import WebAgent, AndroidAgent

logger.remove()
logger.add(sys.stdout, level="INFO")


async def main():
    # Web 端
    ui_agent = await WebAgent.create(simulate_device='iPhone 15 Pro Max', debug=False)

    # # 移动端
    # ui_agent = await AndroidAgent.create(serial=None,platform=Platform.QY)

    await ui_agent.run("""
            - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
            - 点击 "查找"按钮
            - 在输入框输入"任素汐"
        """)


if __name__ == "__main__":
    asyncio.run(main())
