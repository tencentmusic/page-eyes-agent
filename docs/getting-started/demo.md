# 使用示例


## 移动端（Android）

```Python
import asyncio

from page_eyes.agent import AndroidAgent


async def main():
    android_agent = await AndroidAgent.create(serial='android-udid')

    await android_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 如果出现 "close" 按钮，则点击 "close" 按钮, 否则跳过
        - 点击"搜索"
        - 在搜索输入框中输入"任素汐"
        - 等待3秒，直到出现"在腾讯音乐由你榜内相关歌曲"
        - 向上滑动，直到出现"胡广生"
        """
    )


if __name__ == "__main__":
    asyncio.run(main())
```

## 移动端（Harmony Next）

```Python
import asyncio

from page_eyes.agent import HarmonyAgent


async def main():
    harmony_agent = await HarmonyAgent.create(connect_key='hdc-connect-key')

    await harmony_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 如果出现 "close" 按钮，则点击 "close" 按钮, 否则跳过
        - 点击"搜索"
        - 在搜索输入框中输入"任素汐"
        - 等待3秒，直到出现"在腾讯音乐由你榜内相关歌曲"
        - 向上滑动，直到出现"胡广生"
        """
    )


if __name__ == "__main__":
    asyncio.run(main())
```


## 移动端（iOS）

```Python
import asyncio

from page_eyes.agent import IOSAgent


async def main():
    ios_agent = await IOSAgent.create(wda_url='http://xx.xx.xx.xx:8100')

    await ios_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 检查页面是否有 "close" 按钮，如果有则点击 "close" 按钮
        - 进入日榜
        - 点击排名第一的歌曲名
        """
    )


if __name__ == "__main__":
    asyncio.run(main())
```


## PC Web端

```Python
import asyncio

from page_eyes.agent import WebAgent


async def main():
    web_agent = await WebAgent.create(simulate_device='Intel MacBook Pro 13-inch', debug=True)

    await web_agent.run(
        """
        - 打开 url "https://wma.wavecommittee.com/"
        - 点击"浪潮评委会成员"tab
        - 上滑页面，直到出现"查看浪潮评委会"
        - 点击"查看浪潮评委会"按钮
        """
    )


if __name__ == "__main__":
    asyncio.run(main())
```


