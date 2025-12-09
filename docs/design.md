# 系统设计说明（Design Document）

本文简要说明空气质量可视分析系统的架构、模块划分与交互设计，方便在期末报告或 PPT 中引用。

---

## 1. 系统整体架构

从宏观上看，系统可以分为三层：

1. **数据层（Data Layer）**
   - 输入：`data/raw/` 或 `data/sample_raw/` 中的逐小时 CSV
   - 输出：`data/processed/` 下的 `hourly.parquet` 与 `daily_city.parquet`
   - 主要脚本：
     - `src/ingest.py`：递归扫描原始 CSV，合并为长表
     - `src/preprocessing.py`：数据清洗与特征派生
     - `src/aggregations.py`：多粒度聚合（城市-日）

2. **逻辑层（Logic / Analytics Layer）**
   - 提供可重用的数据分析逻辑：
     - `forecasting.py`：基于随机森林的简单预测模型
     - 常用字段与路径配置集中在 `config.py`
   - 对上层视图隐藏复杂的数据处理细节

3. **表现层（Presentation / Visualization Layer）**
   - 基于 Streamlit + Plotly 实现的交互式前端
   - 主要文件：
     - `app.py`：主入口，负责布局、侧边栏筛选、Tab 切换
     - `views/`：各个视图模块（地图、时间序列、组成、故事）

你可以在报告中画出类似“分层架构图”，展示从原始数据到可视分析界面的完整流。

## 2. 模块划分

### 2.1 `config.py`

- 定义项目根目录、数据目录、Parquet 输出路径等
- 集中配置污染物字段与 AQI 等级划分，便于统一管理

### 2.2 `ingest.py`

- 主要职责：
  - 遍历 `sample_raw/` 或 `raw/` 目录下的所有 CSV
  - 合并为一个长表 DataFrame
  - 调用 `preprocess_hourly` 与 `aggregate_daily_city`
  - 将结果写出为 Parquet
- 支持命令行参数：
  - `--use-raw` / `--use-sample`
  - `--no-overwrite`

### 2.3 `preprocessing.py`

- 数据清洗与特征工程：
  - 时间解析（`timepoint -> timestamp`）
  - 衍生字段：`year`, `month`, `day`, `hour`, `season`
  - 统一城市/站点命名：`city`, `station_name`
  - 数值字段类型转换与简单异常值过滤

### 2.4 `aggregations.py`

- 将站点-小时级数据聚合到城市-日级：
  - 日平均 AQI 与各污染物浓度
  - 日最大 AQI 与重污染小时数

### 2.5 `forecasting.py`

- 将时间序列转换为监督学习问题：
  - 使用过去 `n_lags` 个小时作为特征，预测下一个时间步
- 使用 RandomForestRegressor 训练模型
- 支持迭代预测未来 `horizon_hours` 小时
- 当样本不足时回退到持久性预测

### 2.6 `views/`

- `map_view.py`：
  - 使用 Plotly `scatter_geo` 展示最新时间片的空间分布
- `time_view.py`：
  - 支持“按小时/按日”切换的折线图
- `composition_view.py`：
  - 柱状图展示多城市污染物平均浓度
  - 雷达图展示单城市污染物构成
- `story_view.py`：
  - 自动识别典型污染过程，用阴影区域在时间序列中高亮

## 3. 交互设计

### 3.1 全局筛选

- 位于 Streamlit 的 sidebar：
  - 日期范围选择器：控制时间窗口
  - 城市多选：聚焦一组城市
  - 指标选择：AQI / PM2.5 / PM10 / NO₂ / SO₂ / O₃ / CO
- 所有视图共用同一份筛选结果，保证多视图一致性

### 3.2 多视图布局

- 顶部：
  - 四个 KPI 卡片，展示平均 AQI、最优/最差城市、重污染天数
- 主区域：
  - 通过 Tab 切换四种视图：总览 / 组成分析 / 数据故事 / 预测
  - 总览 Tab 内部使用左右两列布局（地图 + 时间序列）

### 3.3 视觉风格

- 使用 `st.set_page_config(layout="wide")` 充分利用宽屏
- 自定义 CSS：
  - 统一字体与背景色
  - 卡片式指标视觉风格
  - 隐藏默认菜单 / footer（更像独立应用）
- Plotly 图表：
  - 合理使用颜色映射（例如 AQI 使用 `RdYlGn_r`）
  - 开启 hover 工具提示与 range slider

## 4. 可扩展性

- 数据层：
  - 可以很容易接入更多年份、更多城市或额外的气象数据
- 算法层：
  - 可在 `forecasting.py` 中替换或增加更复杂的模型
- 表现层：
  - 可以继续添加新的 Tab，例如“健康风险评估”、“政策模拟”等

---

在期末报告和答辩中，你可以基于本设计说明：
- 展示系统架构图和模块依赖关系
- 强调多视图联动和交互设计
- 说明该系统具备良好的扩展性和研究潜力
