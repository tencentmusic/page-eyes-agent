import asyncio
import sys

from loguru import logger

from ieyes_agent.agent import WebAgent, MobileAgent
from ieyes_agent.util.platform import Platform
from typing import cast
try:
    from loguru import BasicHandlerConfig
except ImportError:
    pass


logger.configure(handlers=cast(list['BasicHandlerConfig'], [{"sink": sys.stdout, "level": "INFO"}]))


async def main():
    # Web 端
    ui_agent = await WebAgent.create(simulate_device='iPhone 15 Pro Max', debug=True)

    # 移动端
    # ui_agent = await MobileAgent.create(serial='10.91.145.46:56000',platform=Platform.QY)

    # report = await ui_agent.run(
    #     ('1.打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"\n'
    #      # '2.点击"播放按钮"\n'
    #      '2.点击"查找icon"\n'
    #      '3.在搜索输入框中输入"年轮"\n'
    #      '4.点击"年轮> "\n'
    #      '5.点击"日榜"'
    #      ))

    # report = await ui_agent.run("""
    # 打开 url https://yobang.tencentmusic.com/chart-h5/annual-report-2025-mid/ending?slideId=main
    # 1. 向下滚动最多10次，直到页面中出现 "搜索2025年上榜歌手" 元素;
    # 2. 点击 "搜索";
    # 3. 输入"周";
    # 4. 点击"周杰伦" 最多3次 , 直到页面中出现 "2025年上半年成绩单" 元素
    # """)

    report = await ui_agent.run(
        ('1.打开 url "https://yobang.tencentmusic.com/chart-h5/annual-report-2025-mid/tmeChart?slideId=main"\n'
         '2.不断向上滑动，直到屏幕出现"歌手你好"的元素\n'
         ))

    # report = await ui_agent.run(
    #     (
    #         '1 打开 url "https://yobang.tencentmusic.com/chart-h5/annual-report-2025-mid/ending?slideId=main"\n'
    #         '2 点击"close"关闭弹窗，若弹窗不存在则跳过 \n'
    #         '3 向上滑动最多10次，直到页面中出现"搜索2025年上榜歌手"元素\n'
    #         '4 点击"搜索"\n'
    #         '5 输入"周杰伦"，进入下一步 \n'
    #         '6 点击最多3次"周杰伦 >"，直到页面中出现！"2025年上半年成绩单"元素 \n'
    #         '7 向上滑动3次'
    #      ))

    # await ui_agent.run(
    #     ('1 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"\n'
    #      '2 点击第一个推荐按钮\n'
    #      '3 点击单曲购买\n'
    #      '4 点击"超会连续包月"\n'
    #      '5 点击"立即购买"'
    #      ))


if __name__ == "__main__":
    asyncio.run(main())
