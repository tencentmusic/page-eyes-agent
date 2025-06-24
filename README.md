## 安装依赖
```shell
uv sync
```

## 发布包
首先更新 `pyproject.toml` 中的版本号，然后执行如下命令
```shell
uv build
uv publish --index tencent_pypi
```