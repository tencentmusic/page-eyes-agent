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

## 更新日志
1. 精简了系统提示词，每次调用使用更少的token
2. 优化报告的记录和生成逻辑，解决步骤偶然错乱的问题
3. 优化工具的参数，实现最小化参数，减少token
4. 优化了等待逻辑，实现更精准的等待，不需要统一等待1s
5. 截图、解析改成异步,并发不阻塞
6. 优化浏览器配置，支持使用持久化缓存，二次启动页面速度更快