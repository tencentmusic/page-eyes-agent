import asyncio
import sys

from loguru import logger

from ieyes_agent.agent import WebAgent, MobileAgent
from ieyes_agent.util.platform import Platform
from typing import cast
from ieyes_agent.config import settings
try:
    from loguru import BasicHandlerConfig
except ImportError:
    pass


logger.configure(handlers=cast(list['BasicHandlerConfig'], [{"sink": sys.stdout, "level": "INFO"}]))


async def main():
    logger.info(f'settings: {settings}')
    # Web 端
    ui_agent = await WebAgent.create('openai:deepseek-v3')

    # 移动端
    # ui_agent = await MobileAgent.create('openai:deepseek-v3', platform=Platform.KG)

    # await ui_agent.run('1.点击 Find icon\n2.在搜索输入框中输入"小美满"\n3.点击"小美满> "\n4.点击"查看更多成绩"')
    # await ui_agent.run('1.点击第一个推荐按钮\n2.点击单曲购买\n3.点击"超会连续包月"\n4.点击"立即购买"')

    await ui_agent.run(
        ('1.打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"\n'
         '2.点击"查找icon"\n'
         '3.在搜索输入框中输入"小美满"\n'
         # '4.点击"小美满> "\n'
         # '5.点击"日榜"'
         ))

    # await ui_agent.run(
    #     ('1 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"\n'
    #      '2 点击第一个推荐按钮\n'
    #      '3 点击单曲购买\n'
    #      '4 点击"超会连续包月"\n'
    #      '5 点击"立即购买"'
    #      ))


if __name__ == "__main__":
    asyncio.run(main())
