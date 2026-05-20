# LinerDT — 班轮航运数字孪生仿真平台

基于 Agent 的离散事件仿真（Agent-based DES）平台，完整模仿 **AnyLogic** 树形层次化组织方式，对 AEU（Asia-Europe Express）航线进行数字孪生建模与仿真分析。

---

## 项目架构

```
LinerDT/
├── backend/                          # Python FastAPI 后端
│   ├── app/
│   │   ├── api/                      # RESTful API 端点
│   │   │   ├── sim.py                #   仿真控制 + Agent 树 CRUD
│   │   │   ├── websocket.py          #   WebSocket 实时状态推送
│   │   │   ├── ai.py                 #   AI 对话接口
│   │   │   ├── kpi.py                #   KPI 数据接口
│   │   │   ├── carbon.py             #   碳排放分析接口
│   │   │   ├── experiment.py         #   实验管理（参数扫描/Monte Carlo）
│   │   │   ├── statistics.py         #   统计分析接口
│   │   │   └── academic_lab.py       #   学术实验室接口
│   │   ├── core/                     # 核心框架
│   │   │   ├── tree.py               #   AnyLogic 树形框架（ActiveObject/Agent/Engine/AgentPopulation）
│   │   │   ├── agent_registry.py     #   Agent 类型注册表单例（前端 Palette）
│   │   │   └── config.py             #   全局配置
│   │   ├── scheduler/                # 仿真引擎
│   │   │   ├── scheduler.py          #   SimulationModel + 事件驱动调度器 + ShipAgent/PortAgent
│   │   │   ├── simulation_runner.py  #   全局仿真循环（异步任务管理器）
│   │   │   ├── event_queue.py        #   最小堆事件队列
│   │   │   ├── events.py             #   事件类型定义
│   │   │   └── visualization_sync.py #   可视化同步层
│   │   ├── models/                   # 领域模型
│   │   │   └── ship.py               #   船舶状态机（ShipState）
│   │   ├── schema/                   # 参数声明系统
│   │   │   └── parameter_def.py      #   ParameterDef（兼容旧格式）+ 树形 Parameter（新格式）
│   │   ├── services/                 # 服务层
│   │   │   ├── navigation.py         #   航线导航（haversine 距离、燃油消耗）
│   │   │   ├── kpi_calculator.py     #   KPI 计算引擎
│   │   │   ├── uncertainty.py        #   不确定性模型（天气延误、港口拥堵）
│   │   │   ├── eca.py                #   排放控制区（ECA）燃油切换
│   │   │   ├── distributions.py      #   概率分布模型
│   │   │   ├── ais_adapter.py        #   AIS 数据适配器
│   │   │   ├── or_solver.py          #   运筹学求解器
│   │   │   ├── ml_pipeline.py        #   机器学习管线
│   │   │   ├── report_generator.py   #   报告生成器
│   │   │   ├── statistical_analysis.py # 统计分析工具
│   │   │   └── ...                   #   更多服务
│   │   ├── ai/                       # AI 模块
│   │   │   ├── ai_integration.py     #   AI 集成入口
│   │   │   ├── conversational_engine.py # 对话引擎
│   │   │   ├── decision_agent.py     #   决策 Agent
│   │   │   ├── llm_decision_agent.py #   LLM 驱动决策
│   │   │   ├── decision_rules.py     #   决策规则引擎
│   │   │   ├── experiment_framework.py # AI 实验框架
│   │   │   └── ...                   #   更多 AI 组件
│   │   ├── data/                     # 静态数据
│   │   │   └── aeu_data.py           #   AEU 航线港口/船舶数据
│   │   └── main.py                   # FastAPI 应用入口
│   ├── tests/                        # 192+ 单元测试
│   │   ├── test_agent_crud.py        #   Agent 树 CRUD 操作测试
│   │   ├── test_scheduler_correctness.py # 调度正确性测试
│   │   ├── test_full_simulation.py   #   全流程仿真测试
│   │   ├── test_carbon_emissions.py  #   碳排放测试
│   │   ├── test_kpi_consistency.py   #   KPI 一致性测试
│   │   └── ...                       #   更多测试
│   └── requirements.txt
│
├── frontend/                         # Next.js 14 前端
│   ├── app/
│   │   └── page.tsx                  # 主页面（AppShell IDE 布局）
│   ├── components/
│   │   ├── ide/                      # IDE 布局组件
│   │   │   ├── AppShell.tsx          #   应用外壳（ActivityBar + Sidebar + Workspace）
│   │   │   ├── ActivityBar.tsx       #   左侧活动栏
│   │   │   ├── Sidebar.tsx           #   侧边栏面板容器
│   │   │   ├── Workspace.tsx         #   工作区标签页
│   │   │   ├── Workbench.tsx         #   实验工作台
│   │   │   └── ModuleMarket.tsx      #   模块市场
│   │   ├── AgentTreeEditor.tsx       # Agent 树编辑器（AnyLogic 风格层次树）
│   │   ├── AgentDetailPanel.tsx      # Agent 属性面板（右侧栏）
│   │   ├── AIChatPanel.tsx           # AI 对话面板（右侧栏）
│   │   ├── ControlPanel.tsx          # 仿真控制栏
│   │   ├── SimulationConfig.tsx      # 仿真配置面板
│   │   ├── map/                      # 地图组件
│   │   │   ├── MapContainer.tsx      #   地图容器（Leaflet/Cesium 切换）
│   │   │   ├── LeafletMap.tsx        #   2D 地图
│   │   │   ├── CesiumGlobe.tsx       #   3D 地球
│   │   │   └── MapToggle.tsx         #   2D/3D 切换
│   │   ├── dashboard/                # 仪表盘组件
│   │   │   ├── KPIWithTrend.tsx      #   KPI 指标卡
│   │   │   ├── ModernGauge.tsx       #   仪表盘
│   │   │   ├── RadialBarChart.tsx    #   径向条形图
│   │   │   ├── PortGrid.tsx          #   港口网格
│   │   │   ├── RealTimeMonitor.tsx   #   实时监控
│   │   │   └── AcademicStatsPanel.tsx #   学术统计面板
│   │   ├── academic/                 # 学术实验组件
│   │   │   ├── ORLab.tsx             #   运筹学模型实验室
│   │   │   ├── DataLab.tsx           #   数据浏览实验室
│   │   │   ├── MLLab.tsx             #   机器学习实验室
│   │   │   ├── NotebookLab.tsx       #   学术笔记本实验室
│   │   │   └── ReportLab.tsx         #   报告生成实验室
│   │   ├── experiment/               # 实验组件
│   │   │   ├── ParameterSweep.tsx    #   参数扫描
│   │   │   ├── MonteCarloAnalysis.tsx #   Monte Carlo 分析
│   │   │   ├── WhatIfScenarios.tsx   #   What-if 场景对比
│   │   │   └── ReportGenerator.tsx   #   实验报告生成
│   │   ├── ShipGantt.tsx             # 船舶甘特图
│   │   ├── DelayNetwork.tsx          # 延误传播网络图
│   │   ├── ParameterEditor.tsx       # 参数编辑器
│   │   ├── CarbonVisualization.tsx   # 碳排放可视化
│   │   └── ui/                       # 通用 UI 组件
│   ├── hooks/
│   │   ├── useWebSocket.ts           # WebSocket 实时数据 hook
│   │   └── useAIChat.ts              # AI 对话 hook
│   ├── types/
│   │   └── simulation.ts             # TypeScript 类型定义
│   └── package.json
│
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── .env.example
```

---

## 核心技术架构

### 1. AnyLogic 风格树形 Agent 框架

采用与 AnyLogic 高度一致的层次化对象组织方式：

```
Engine ("engine")                          # 仿真引擎（根节点）
└── SimulationModel ("model")              # 仿真模型
    ├── ShipAgent ("s001")                 # 船舶 Agent
    ├── ShipAgent ("s002")
    ├── PortAgent ("SHA")                  # 港口 Agent
    │   └── AgentPopulation ("cranes")     # Agent 群体（岸桥集合）
    │       ├── CraneAgent ("crane_1")
    │       └── CraneAgent ("crane_2")
    └── PortAgent ("NGB")
```

**核心类层次：**

| 类 | 职责 |
|---|---|
| `ActiveObject` | 树节点基类，管理 `_owner`/`_embedded` 双向导航 |
| `Agent` | 拥有参数系统 + 生命周期钩子（`on_create`/`on_destroy`） |
| `AgentPopulation` | Agent 群体容器，类似 AnyLogic 的 Population，支持 `add()`/`remove()` |
| `Engine` | 仿真引擎根节点，持有时间状态 |
| `Parameter` | 新参数声明系统（支持分组、类型、范围校验） |
| `ParameterDef` | 旧参数声明系统（兼容过渡用） |

**树形导航能力：**

- `get_full_path()` → `"engine.model.SHA.cranes.crane_1"`
- `resolve("engine.model.SHA")` → 按路径查找 Agent
- `embed(child, name)` → 将子节点嵌入当前节点
- `to_tree_dict()` → 序列化整棵子树供前端渲染

### 2. 事件驱动仿真引擎

- **EventDrivenScheduler**: 基于最小堆（`heapq`）事件队列的调度器
- **事件类型**: 离港、到港、泊位分配、装卸完成、燃油切换、CII 检查等
- **仿真模式**: 学术模式（批量推进） / 实时模式（Wall-clock 同步）
- **全局仿真循环**: 单一 `asyncio.Task` 确保无竞争条件

### 3. 前端 IDE 布局

采用 VS Code 风格 IDE 布局：

```
┌─────────┬────────────────┬─────────────┐
│ Activity │   Workspace    │  Right      │
│  Bar     │   (Tabs)       │  Sidebar    │
│          │                │ (AI / Agent │
│  🔧 配置 │  ┌──────────┐  │  属性)     │
│  🌳 Agent│  │  地图/    │  │             │
│  🔬 实验 │  │  分析/    │  │             │
│          │  │  教学     │  │             │
│          │  └──────────┘  │             │
├─────────┴────────────────┴─────────────┤
│  控制栏（播放/暂停/速度/2D-3D切换）    │
└─────────────────────────────────────────┘
```

- **左侧栏**: 仿真配置 / Agent 树编辑器 / 实验工作台
- **右侧栏**: AI 对话 / Agent 属性面板（共享同一位置）
- **工作区**: 地图（2D/3D）/ 数据分析 / 教学模式
- **控制栏**: 仿真启停、速度调节、地图切换

### 4. Agent 动态 CRUD

Agent 可以在运行时动态创建、编辑和删除：

| 端点 | 功能 |
|---|---|
| `GET /api/sim/tree` | 返回完整 Agent 树 |
| `GET /api/sim/tree/types` | 列出可创建的 Agent 类型（Palette） |
| `POST /api/sim/tree/agent` | 创建 Agent（指定父路径、类型、参数） |
| `GET /api/sim/tree/agent?path=` | 获取单个 Agent 详情（参数+当前值） |
| `DELETE /api/sim/tree/agent?path=` | 删除 Agent |
| `POST /api/sim/tree/parameters` | 批量设置参数 |

### 5. AI 集成

- **对话引擎**: 自然语言查询仿真状态、KPI、延误分析
- **决策 Agent**: LLM 驱动的航速优化、CII 合规决策
- **规则引擎**: 可配置的决策规则系统
- **实验框架**: AI 辅助的参数扫描和场景分析

### 6. 服务层

| 服务 | 功能 |
|---|---|
| **航线导航** | Haversine 距离计算、燃油消耗模型（三次方律） |
| **KPI 计算** | 准班率、CII 评级、泊位利用率、系统韧性指数 |
| **不确定性模型** | 天气延误概率、港口拥堵分布、蒙特卡洛随机性 |
| **ECA 合规** | 排放控制区燃油切换（VLSFO ↔ MGO） |
| **统计分析** | 假设检验、敏感性分析、效应量（Cohen's d） |
| **实验管理** | 参数扫描、Monte Carlo、What-if 场景对比 |

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- npm 或 yarn

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:3000`，后端 API 在 `http://localhost:8000`。

### 运行测试

```bash
cd backend
python -m pytest tests/ -v      # 全部测试
python -m pytest tests/test_agent_crud.py -v  # Agent CRUD 测试
```

---

## 技术栈

| 层 | 技术 |
|---|---|
| **后端框架** | FastAPI, Pydantic, Uvicorn |
| **仿真引擎** | 自定义事件驱动调度器（最小堆事件队列） |
| **前端框架** | Next.js 14 (React), TypeScript |
| **地图** | Leaflet (2D) / Cesium.js (3D) |
| **可视化** | ECharts, Three.js |
| **AI** | Anthropic Claude API, LLM 决策 Agent |
| **数据库** | 无（纯内存仿真，状态通过 WebSocket 实时推送） |
| **测试** | Pytest (192+ 测试) |
| **部署** | Docker, Docker Compose |

---

## API 概览

| 前缀 | 路由 | 说明 |
|---|---|---|
| `/api/sim` | `GET /tree`, `POST /tree/agent`, ... | 仿真控制和 Agent 树管理 |
| `/api/kpi` | `GET /dashboard`, `GET /trend` | KPI 指标数据 |
| `/api/carbon` | `GET /emissions`, `GET /cii` | 碳排放分析 |
| `/api/ai` | `POST /chat` | AI 对话 |
| `/api/experiment` | `POST /sweep`, `POST /monte-carlo` | 实验管理 |
| `/api/stats` | `POST /hypothesis-test`, ... | 统计分析 |
| `/ws` | WebSocket | 实时仿真状态推送 |
| `/api/health` | `GET` | 健康检查 |

---

## 开发规划

- 阶段 0：骨架搭建 — 项目跑起来，地图显示 ✅
- 阶段 1：仿真核心 — 9艘船按 AEU 航线运行 ✅
- 阶段 2：可视化 MVP — 船沿航线平滑移动 ✅
- 阶段 3：仿真完善 — 泊位排队、延误涌现 ✅
- 阶段 4：仪表盘 — ECharts 实时 KPI ✅
- 阶段 5：AI Level 1 — 自然语言查询 ✅
- 阶段 6：AI Level 2 + 碳排放 — AI 调参、CII 自调节 ✅
- 阶段 7：AnyLogic 树形重构 — Agent 层次化、动态 CRUD、属性面板 ✅
- 阶段 8：画布编辑器 — 可视化编辑 Agent 逻辑（规划中）
