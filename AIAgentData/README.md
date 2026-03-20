# AIAgentData

用于 LaViC AgentData 模型资产生成、修复与打包的脚本工程。

## 1. 环境准备

```bash
cd /Users/qiaoyanshuo/AIProduct/codexproject/agentmodelbuilder/AIAgentData
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 环境变量

参考 `.env.example`。

最少需要：
- `RODIN_API_KEY`（使用 Rodin 相关脚本时必填）

可选：
- `AIALAVIC_PROXY_URL`
- `AIALAVIC_MODELS_DIR`
- `AIALAVIC_DOWNLOADS_DIR`
- `AIALAVIC_ALLOW_PLACEHOLDER=1`（默认关闭占位资源）

## 3. 统一入口（CLI）

列出命令：

```bash
python src/cli.py list
```

常用命令：

```bash
python src/cli.py validate
python src/cli.py validate-all
python src/cli.py pipeline -- --pipeline validate
python src/cli.py pipeline -- --pipeline full --dry-run
python src/cli.py fix-zip
python src/cli.py zip
python src/cli.py gen-mil-symbols
```

说明：
- `pipeline` 是统一编排入口。
- `--` 后面的参数会透传给 `orchestrator.py`。
- 示例：`python src/cli.py pipeline -- --pipeline air`。

## 4. CI 校验

CI 文件：`.github/workflows/ci.yml`

执行内容：
- `python -m py_compile src/*.py`
- `python src/validate_all.py`
