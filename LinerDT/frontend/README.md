# LinerDT Frontend

Next.js 14 前端，基于 AppShell IDE 布局，包含 Agent 树编辑器、AI 对话、实时地图监控和数据分析仪表盘。

## 组件架构

- **`ide/`** — AppShell 外壳（ActivityBar + Sidebar + Workspace），VS Code 风格布局
- **`AgentTreeEditor.tsx`** — AnyLogic 风格层次化 Agent 树编辑器
- **`AgentDetailPanel.tsx`** — Agent 属性面板（右侧栏，与 AI 对话共享位置）
- **`AIChatPanel.tsx`** — AI 对话面板
- **`map/`** — Leaflet 2D / Cesium 3D 地图
- **`dashboard/`** — ECharts KPI 仪表盘
- **`academic/`** — 学术实验室（OR/ML/数据/笔记本/报告）
- **`experiment/`** — 实验组件（参数扫描/Monte Carlo/What-if）

## 开发

```bash
npm install
npm run dev     # 开发服务器 :3000
npm run build   # 生产构建
npx tsc --noEmit    # TypeScript 类型检查
```

## 环境变量

参见 `.env.local.example`。
