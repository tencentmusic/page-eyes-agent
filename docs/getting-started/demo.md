# 使用示例


## 移动端（Android）

```Python
import asyncio

from page_eyes.agent import WebAgent, MobileAgent


async def main():
    # 移动端
    ui_agent = await MobileAgent.create(serial='android-udid')

    report = await ui_agent.run(
        ('1.打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"\\n'
         '2.点击"查找icon"\\n'
         '3.在搜索输入框中输入"小美满"\\n'
         '4.点击"小美满> "\\n'
         '5.点击"日榜"'
         ))


if __name__ == "__main__":
    asyncio.run(main())
```


## 移动端（iOS）

```Python
import asyncio

from page_eyes.agent import IOSAgent


async def main():
    # iOS 移动端
    ui_agent = await IOSAgent.create(wda_url='http://xx.xx.xx.xx:8100')

    report = await ui_agent.run(
        ('1.打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"\\n'
         '2.点击"查找icon"\\n'
         '3.在搜索输入框中输入"小美满"\\n'
         '4.点击"小美满> "\\n'
         '5.点击"日榜"'
         ))


if __name__ == "__main__":
    asyncio.run(main())
```


## PC Web端
```Python
import asyncio

from page_eyes.agent import WebAgent, MobileAgent

async def main():
    # PC Web端
    ui_agent = await WebAgent.create(simulate_device='Intel MacBook Pro 13-inch', debug=True)

    report = await ui_agent.run(
        ('1.打开 url "https://wma.wavecommittee.com/"\n'
         '2.点击"浪潮评委会成员"tab\n'
         '3.上滑页面，直到出现"查看浪潮评委会"\n'
         '4.点击"查看浪潮评委会"按钮\n'
         ))


if __name__ == "__main__":
    asyncio.run(main())
```


