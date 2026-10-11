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
- `data/raw/ura_mp2019_planning_areas.geojson`：URA 官方规划区边界，用于 Town 的近似地图展示；附带来源和校验元数据。
- `data/processed/`：清洗表、候选编码特征、质量统计、相关性和异常审查表。
- `uv.lock`：锁定本次使用的依赖版本。

默认复用快照。若数据文件不存在，notebook 会通过官方 API 下载并截取；设置 `REFRESH_DATA = True` 可以覆盖刷新，之后应恢复为 `False`。数据源可能回修历史记录，刷新后应复核 notebook 中的固定结论。原始快照及处理结果不纳入 Git。

Notebook 的 Markdown 说明全部使用英文。类别比例使用饼图，小于 1% 的类别仅在图中合并；数值分布使用 Histogram + KDE + 四分位数参考线。各变量与价格的关系图统一放在相关性分析之后。

完全重复的记录共有 308 组：307 组双行、一组三行，共 617 行；每组保留一行后有 309 条额外行。主分析保留这些行和 IQR 离群值，另做敏感性比较。租期与近似公式偏差超过 1 年的 128 条记录因原因无法确定而排除，审查记录保存在 `lease_excluded_records.csv`；剩余 221,938 条用于 EDA。

地址采用全局 → Town → Town + Street → Town + Street + Block 的层级平滑 target encoding，演示平滑强度分别为 50、20、10。每年的编码仅使用此前年份的价格；2017 年作为历史预热，2018–2024 为训练候选，2025 为测试候选。模型特征使用最终楼栋级编码并排除租约开始年份，尚未训练模型。地图使用规划区代理边界，未将交易精确定位到住宅单元或规划子区。

完整作业仍需基础模型的预处理前后比较、进一步调查和视频；初步 notebook 已包含 AI 使用声明与后续工作说明。
