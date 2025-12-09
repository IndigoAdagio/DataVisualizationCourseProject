# Real-time-inspired Visual Analytics of Urban Air Quality in China (2022–2025)

中国城市空气质量多视图可视分析系统 —— 期末大作业示例项目。

本项目基于 Streamlit + Plotly + Pandas，构建一个多视图（地图 + 时间序列 + 污染物组成 + 数据故事 + 简单预测）的空气质量可视分析系统。
项目自带一份小规模示例数据集，解压后即可运行；也支持你在 `data/raw/` 目录放入真实完整数据，并通过 `ingest.py` 自动构建处理后的
Parquet 数据集。

## 1. 项目结构

```text
air_quality_analytics/
├── app.py                     # Streamlit 主入口
├── requirements.txt
├── README.md
├── data/
│   ├── sample_raw/            # 附带的小规模示例原始数据（按日期文件夹存放）
│   ├── raw/                   # 放置你的真实完整原始数据（结构与 sample_raw 相同）
│   └── processed/
│       ├── hourly.parquet     # 站点-小时级别合并数据（由 ingest.py 生成）
│       └── daily_city.parquet # 城市-日聚合数据（由 ingest.py 生成）
├── src/
│   ├── __init__.py
│   ├── config.py              # 路径配置、常量
│   ├── ingest.py              # 原始 CSV 导入、合并、写出 Parquet
│   ├── preprocessing.py       # 清洗、类型转换、派生时间/季节字段等
│   ├── aggregations.py        # 聚合到城市-日等粒度
│   ├── forecasting.py         # 简单预测模块（随机森林 + 滞后特征）
│   └── views/
│       ├── __init__.py
│       ├── map_view.py        # 空间分布地图视图
│       ├── time_view.py       # 时间序列视图
│       ├── composition_view.py# 污染物组成视图（柱状 + 雷达）
│       └── story_view.py      # 数据故事视图
└── docs/
    ├── report_outline.md      # 课程期末报告结构建议
    └── design.md              # 系统架构与交互设计说明
```

## 2. 快速开始（使用示例数据）

1. 安装依赖（建议在虚拟环境中）：

   ```bash
   pip install -r requirements.txt
   ```

2. 运行可视分析系统：

   ```bash
   streamlit run app.py
   ```

   首次运行时，如果 `data/processed/` 目录下没有 `hourly.parquet` 与 `daily_city.parquet`，
   程序会自动使用 `data/sample_raw/` 中的小示例数据构建处理后的数据集。

## 3. 使用真实完整数据

1. 将你已收集好的逐小时空气质量 CSV 文件放入：

   ```text
   data/raw/YYYY-MM-DD/YYYY-MM-DDTHH.csv
   ```

   目录结构与 `data/sample_raw/` 中的示例一致。

2. 在项目根目录执行：

   ```bash
   # 基于 data/raw/ 中的真实数据构建处理后的 Parquet 数据
   python src/ingest.py --use-raw
   ```

   生成完成后，会在 `data/processed/` 中看到：

   - `hourly.parquet`
   - `daily_city.parquet`

3. 再次运行 Streamlit：

   ```bash
   streamlit run app.py
   ```

   此时系统将基于真实数据进行可视分析。

## 4. 模块说明（简要）

- `src/config.py`：
  定义数据目录、Parquet 文件路径、污染物字段等常量。

- `src/ingest.py`：
  从 `sample_raw/` 或 `raw/` 目录递归扫描所有 CSV，合并为长表，调用预处理和聚合函数，输出为 Parquet 文件。
  可作为报告中的“数据处理流程”部分。

- `src/preprocessing.py`：
  完成时间字段解析（年/月/日/小时/季节）、数据类型转换、异常值简单过滤等。

- `src/aggregations.py`：
  将站点-小时级别数据聚合为城市-日级数据，用于长期趋势和 KPI 指标展示。

- `src/views/*.py`：
  各自负责一个视图：地图、时间序列、组成分析、数据故事。方便在报告中画系统架构图。

- `src/forecasting.py`：
  简单的基线预测模块，使用滞后窗口特征 + RandomForestRegressor 对未来若干小时 AQI / PM2.5 做预测。

- `docs/report_outline.md`：
  提供期末报告结构建议、每节应写内容和可选的数据故事示例。

- `docs/design.md`：
  总结系统架构、模块划分和交互设计思路，可直接引用到报告中。

## 5. 备注

- 如果你想重新基于示例数据构建处理后的数据集，可以运行：

  ```bash
  python src/ingest.py
  # 或
  python src/ingest.py --use-sample
  ```

- 所有源码中都包含适量中文注释，方便阅读和在报告中引用。
