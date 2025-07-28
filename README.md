## 安装依赖
```shell
uv sync
```

## 发布包
首先更新 `pyproject.toml` 中的版本号，然后执行如下命令
```shell
uv build && uv publish --index tencent_pypi
```

```
    report = await ui_agent.run(
        ('1.打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"\n'
         # '2.点击"播放按钮"\n'
         '2.点击"查找icon"\n'
         '3.在搜索输入框中输入"小美满"\n'
         '4.点击"小美满> "\n'
         '5.点击"日榜"'
         ))
```

```
    await ui_agent.run(
        ('1 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"\n'
         '2 点击第一个推荐按钮\n'
         '3 点击单曲购买\n'
         '4 点击"超会连续包月"\n'
         '5 点击"立即购买"'
         ))
```

```
    report = await ui_agent.run(
        ('1.打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"\n'
         '2.上滑，直到页面中出现"跳楼机"元素\n',
         '3.点击"跳楼机"元素',
         ))
```
```
    report = await ui_agent.run(
        ('1.打开 url "https://chart.tencentmusic.com/uni-chart"\n'
         '2.向下滚动，直到页面中出现"听雨夜"元素\n',
         '3.点击"听雨夜"元素',
         ))
```