# 期末报告结构建议：Real-time-inspired Visual Analytics of Urban Air Quality in China (2022–2025)

> 下述结构是一个“类学术论文”风格的大纲，你可以根据课程要求适当增删。

## 1. 引言（Introduction）
- 研究背景：城市空气质量问题、健康影响、政策需求
- 研究动机：现有平台多为静态图表，缺乏交互式可视分析
- 项目目标：构建支持多视图、多粒度分析的空气质量可视分析系统

## 2. 数据（Data）
- 数据来源与时间范围
- 原始数据结构（站点-小时级，字段说明）
- 数据预处理与清洗步骤（对应 `preprocessing.py`）
- 聚合逻辑（城市-日级，对应 `aggregations.py`）

## 3. 系统架构与方法（System Architecture & Methodology）
- 整体架构图：数据层、逻辑层、表现层
- 模块划分：`config.py`, `ingest.py`, `preprocessing.py`, `aggregations.py`, `forecasting.py`, `views/*.py`
- 预测模块设计：滞后特征 + 随机森林回归

## 4. 可视化设计（Visualization Design）
- 概览视图（Overview）：KPI 指标卡 + 地图 + 时间序列
- 组成视图（Composition）：污染物柱状图 + 雷达图
- 数据故事视图（Story）：自动识别一次典型污染过程，采用高亮阴影区域
- 预测视图（Forecast）：历史曲线 + 未来预测曲线
- **Heatmap 视图（Heatmap）：**
  - 使用 density_mapbox 绘制空间热力图
  - 支持站点级与城市级聚合
  - 响应全局时间 / 城市 / 站点 / 指标筛选

## 5. 实验与分析（Experiments & Analysis）
- 全局模式：多城市 AQI 年度/季节变化趋势
- 城市案例：某城市冬夏对比、某次污染过程分析
- 热力图分析：
  - 展示某一典型时间段的空间污染分布
  - 对比站点级 vs 城市级热力图差异
- 预测效果评估（可选）：使用 MAE/RMSE 等指标

## 6. 讨论（Discussion）
- 数据质量与局限：缺测、异常值、不均匀分布
- 方法局限：预测模型简单，未考虑气象与排放数据
- 可视化局限：移动端适配、性能优化等

## 7. 结论与展望（Conclusion & Future Work）
- 总结主要贡献：多视图可视分析平台 + 基线预测 + 热力图
- 未来工作：
  - 加入更多数据源（气象、交通、工业排放）
  - 尝试更复杂的时空预测模型
  - 开展用户研究评估系统有效性

## 参考文献（References）
- 空气质量相关标准与研究
- 可视分析与信息可视化经典论文
- 所用工具库（Streamlit, Plotly, scikit-learn 等）的官方文档
