# 案例

## QQ音乐Android端自动化

#### 目标
QQ音乐app内，打开腾讯音乐由你榜，给喜爱的歌手投票



> 首先确认本地设备连接成功
```bash
adb devices
```


#### 脚本

```Python
import asyncio

from page_eyes.agent import WebAgent, AndroidAgent


async def main():
    # 移动端，serial=None为本地连接设备
    ui_agent = await AndroidAgent.create(serial=None, platform=Platform.QY)

    report = await ui_agent.run(
        ('1.打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"\n'
         '2.点击关闭弹窗，没有弹窗则跳过步骤\n'
         '3.点击"查找"icon\n'
         '4.搜索输入框内输入"林俊杰"\n'
         '5.点击第一首歌曲的"推荐"按钮\n'
         '6.弹窗内点击"推荐"按钮\n'
         ))


if __name__ == "__main__":
    asyncio.run(main())
```

#### 交互效果

<video
    controls
    preload="metadata"
    poster="https://cdn-y.tencentmusic.com/uni/commonPic/cos_97c5191d0fcf23b752696198a1d722cf74d9cf02.png"
    style="width: 100%; max-width: 640px; border: 1px solid #ccc; display: block; margin-top: 10px;">
    <source src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_15c6ee3e09c218308110c20496f0ad8eb1cfb758.mov" type="video/mp4">
    抱歉，您的浏览器不支持播放此视频。
</video>

---
#### 步骤报告

报告内容为每个步骤对应页面的元素信息详情（包括元素位置、大小、识别内容、周围元素等），方便调试与回顾。

<a href="https://cdn-y.tencentmusic.com/uni/commonPic/cos_4bff676f4f54456f511465314f31f04804d89809.html" target="_blank" title="点击查看完整报告">
    <img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_3e4054e04147abcabdae296a9a67c31bf15d6390.png" alt="步骤报告示例" style="width: 800px; border: 1px solid #ccc; cursor: pointer; vertical-align: middle; margin-top: 10px; margin-bottom: 10px;">
</a>

<details>
  <summary>点击查看元素信息详情示例</summary>
  <img title="元素信息示例" src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_2f75e92b9643a8d9cd4a60706a5947ca038e5f6c.png" style="max-width: 100%; border: 1px solid #eee; margin-top: 10px;">
</details>



## Web浏览器自动化用例

#### 目标
在浪潮音乐大赏官网内，查看浪潮评委会信息，并进入浪潮评委官网


#### 脚本

```Python
import asyncio

from page_eyes.agent import WebAgent, AndroidAgent


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

#### 交互效果

<video
    controls
    preload="metadata"
    poster="https://cdn-y.tencentmusic.com/uni/commonPic/cos_7f7b6d66271258cee95ae8bc374b3a77f7df2d9d.png"
    style="width: 100%; max-width: 640px; border: 1px solid #ccc; display: block; margin-top: 10px;">
    <source src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_fc70e3a4b98618759afd1d45cbff6ee2423220da.mov" type="video/mp4">
    抱歉，您的浏览器不支持播放此视频。
</video>

---
#### 步骤报告

下图为PC端打开页面的元素信息详情

<a href="https://cdn-y.tencentmusic.com/uni/commonPic/cos_2f71a52a5b20e2d356d44c7502feaff1c589f1fe.html" target="_blank" title="点击查看完整报告">
    <img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_4d72c6344c6c8cc2f61881de7361c3e56832a0ef.png" alt="步骤报告示例" style="width: 800px; border: 1px solid #ccc; cursor: pointer; vertical-align: middle; margin-top: 10px; margin-bottom: 10px;">
</a>

<details>
  <summary>点击查看元素信息详情示例</summary>
  <img title="元素信息示例" src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_b8dbb9c9dafd9fcf7c827fb427da3ab0b6b1df04.png" style="max-width: 100%; border: 1px solid #eee; margin-top: 10px;">
</details>


