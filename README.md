# OCC Analyzer v1.0

基于 pythonocc-core + PyQt5 的轻量 3D 几何分析工具。

## 功能
- 拖拽 Shape · 实时最小距离计算
- 导入 STEP / IGES / BREP 文件
- 多形体碰撞检测（可自定义阈值）
- 几何测量（体积 / 表面积 / 包围盒）

## 运行

```bash
# 安装依赖（推荐 conda）
conda create -n occ_env python=3.10
conda activate occ_env
conda install -c conda-forge pythonocc-core pyqt

# 运行
python main.py
```

## 项目结构

```
occ_analyzer/
├── main.py                  # 入口，Qt 后端自动探测
├── requirements.txt
├── core/
│   ├── shape_item.py        # ShapeItem 数据类（几何查询）
│   ├── importer.py          # CAD 文件导入（注册表模式，易扩展）
│   └── analysis.py          # 纯函数：距离 / 碰撞计算
├── viewer/
│   └── occ_viewer.py        # 3D 视口，鼠标拖拽 + 分析信号
├── panels/
│   ├── shapes_panel.py      # Tab：形体管理
│   ├── distance_panel.py    # Tab：实时距离
│   ├── collision_panel.py   # Tab：碰撞检测
│   └── measure_panel.py     # Tab：几何测量
├── ui/
│   ├── main_window.py       # 主窗口，组装与信号路由
│   └── styles.py            # 全局 QSS 样式表
└── utils/
    └── helpers.py           # 通用 Qt / OCC 工具函数
```

## 扩展指引

| 目标 | 修改文件 |
|---|---|
| 新增 CAD 格式 | `core/importer.py` → 注册到 `IMPORTERS` |
| 新增基础体素 | `ui/main_window.py` → 注册到 `_PRIMITIVES_FACTORIES` |
| 新增分析算法 | `core/analysis.py` → 新增函数 + dataclass |
| 新增侧边栏 Tab | `ui/main_window.py` → `_build_sidebar()` 中 `addTab` |
| 切换主题 | `ui/styles.py` → 改为 `ThemeManager` 类 |
| 支持旋转拖拽 | `viewer/occ_viewer.py` → 在 `ShapeItem` 增加 rotation 字段 |
