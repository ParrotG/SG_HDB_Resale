# SG HDB Resale 数据探索

使用 Python 3.11 和 uv，按 `docs/Assignment Procedure.pdf` 完成数据获取、质量检查、字段预处理、EDA、享乐价格回归和预处理对比初稿。

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
- `uv.lock`：锁定本次使用的依赖版本。

默认复用快照。若数据文件不存在，notebook 会通过官方 API 下载并截取；设置 `REFRESH_DATA = True` 可以覆盖刷新，之后应恢复为 `False`。数据源可能回修历史记录，刷新后应复核 notebook 中的固定结论。原始快照及逐条处理后的交易记录不纳入 Git；核心图保存在 `figures/`，扩展分析的汇总表与图分别保存在 `error_analysis_outputs/`、`section16_outputs/` 和 `section17_outputs/`。

Notebook 的 Markdown 说明全部使用英文。类别比例使用饼图，小于 1% 的类别仅在图中合并；数值分布使用 Histogram + KDE + 四分位数参考线。各变量与价格的关系图统一放在相关性分析之后。

完全重复的记录共有 308 组：307 组双行、一组三行。每组保留一条代表记录，排除 309 条多余副本。租期与近似公式偏差超过 1 年的 128 条记录因原因无法确定而排除；最终 221,629 条记录用于 EDA、回归和预测。IQR 标记的有效价格尾部仍予保留，因为训练集删尾会恶化高价测试交易的误差。

地址采用全局 → Town → Town + Street → Town + Street + Block 的层级平滑 target encoding，演示平滑强度分别为 50、20、10。每年的编码仅使用此前年份的价格；预测比较中 2017 年作为历史预热，2018–2024 为最终训练集，2025 为测试集。地图使用规划区代理边界，未将交易精确定位到住宅单元或规划子区。

清洗、统计、编码与相关性结果保留在 notebook 内存和单元格输出中，不导出逐条处理结果。楼层 ordinal 的 KDE 使用较宽带宽（`bw_adjust=4`），减少整数编码导致的逐层波峰。

享乐价格主回归以对数价格为目标，以 BEDOK 为地区参照，逐步控制登记月份、面积、房型/模型、楼层和租期；标准误按 Town + Street + Block 聚类。地区结果是条件关联，不能直接解释为因果效应。共同支持、控制加入顺序和楼层编码敏感性用于界定结论范围。

预测部分使用同一个 OLS 方法逐步比较类别结构、函数形式、对数目标和历史地址编码。所有 B0–B4 变体使用同一清洗样本；时间趋势仅用 2024 年验证集选择，2025 年测试集用于统一评估。后续分析检查 Town/房型误差、等 Town 权重、价格 IQR 限制、时间归一化地址编码和滚动年份表现。

Notebook 已包含 AI 使用声明、Git 贡献记录和随运行结果生成的讨论。视频材料见 [slide points](docs/presentation_slide_points.md) 与 [presentation script](docs/presentation_script.md)。小组提交前仍需独立复核结论并将 Git 名称替换为成员真实姓名。

## 第 15 节：预测误差解释

新增分析检查 BUKIT BATOK、TAMPINES 为什么在 B4 中恶化，以及历史地址编码带来的高估。比较使用同一批 25,009 条清洗后的 2025 年测试交易，保留 B0–B4 的 OLS 方法和 2024 年选择的时间趋势。

- 阶段和月度误差：最大恶化集中在 B3 → B4，两地全年 12 个月均出现 B4 MAE 高于 B0。
- 房型与地址支持度：分配误差恶化的来源，并用 2024 年房型占比标准化；不同地区的地址支持度问题并不相同。
- 模型行为：精确分解 B4 相对 B3 的预测变化，包含地址项、共享系数变化和 smearing。
- 敏感性与不确定性：固定模型冻结最新一年地址历史，并按楼栋做配对 bootstrap；这些都是探索性诊断，不用于选择测试集上的最佳方案。

详细结论和复核步骤见 [预测误差分析说明](docs/prediction_error_analysis.md)。从头执行 notebook 会重新生成 `error_analysis_outputs/` 中的 CSV 与 4 张图；保存的 notebook 输出可直接阅读。

本次复核使用项目锁定的 Python 3.11 环境；整份 notebook 已在同一新内核中执行成功。数据快照校验值与原分析一致，全部绘图均保存为本地 PNG。
