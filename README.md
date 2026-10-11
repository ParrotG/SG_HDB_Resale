# SG HDB Resale 数据探索

使用 Python 3.11 和 uv，按 `docs/Assignment Procedure.pdf` 完成初步数据获取、质量检查、字段预处理、EDA 和价格相关性分析。

## 运行

在项目根目录执行：

```bash
uv sync --locked
uv run jupyter lab
```

打开 `hdb_resale_eda.ipynb`，使用项目 `.venv` 内核并按顺序运行全部单元格。已保存执行输出，可以直接阅读。

## 数据与产物

- `data/raw/hdb_resale_2017_2025.csv`：官方数据截至 2025-12 的快照。
- `data/raw/hdb_resale_2017_2025.metadata.json`：来源、下载时间、日期边界和快照 SHA-256。
- `data/processed/`：清洗表、候选编码特征、质量统计、相关性和异常审查表。
- `uv.lock`：锁定本次使用的依赖版本。

默认复用快照。若数据文件不存在，notebook 会通过官方 API 下载并截取；设置 `REFRESH_DATA = True` 可以覆盖刷新，之后应恢复为 `False`。数据源可能回修历史记录，刷新后应复核 notebook 中的固定结论。原始快照及处理结果不纳入 Git。

完全重复的额外行、IQR 离群值及租期公式偏差均先保留，另做敏感性比较。仅剔除明确不满足解析或业务范围规则的记录；当前快照没有这样的记录。地址只统计层级组合数量，暂不编码。候选模型特征排除租约开始年份，尚未进行模型训练。

完整作业仍需基础模型的预处理前后比较、进一步调查和视频；初步 notebook 已包含 AI 使用声明与后续工作说明。
