'use client'

import { useState, useCallback, useEffect, useRef, ReactNode } from 'react'
import { MapContainer } from '@/components/map'
import { SimNotStarted } from '@/components/common/EmptyState'
import ModernGauge from '@/components/dashboard/ModernGauge'
import RadialBarChart from '@/components/dashboard/RadialBarChart'
import KPIWithTrend from '@/components/dashboard/KPIWithTrend'
import PortGrid from '@/components/dashboard/PortGrid'
import { ShipDetailAnimation, PortMicroView, FadeIn } from '@/components/animations'
import { Card } from '@/components/ui'
import ControlPanel from '@/components/ControlPanel'
import AIChatPanel from '@/components/AIChatPanel'
import SimulationConfig from '@/components/SimulationConfig'
import AcademicStatsPanel from '@/components/dashboard/AcademicStatsPanel'
import RealTimeMonitor from '@/components/dashboard/RealTimeMonitor'
import ShipGantt from '@/components/ShipGantt'
import DelayNetwork from '@/components/DelayNetwork'
import FullScreenDetailView from '@/components/FullScreenDetailView'
import { useWebSocket, SimState, ShipTrajectoryData } from '@/hooks/useWebSocket'
import ReactECharts from 'echarts-for-react'
import type { TrendDataPoint, KpiData, AIDecision, ShipData, PortData } from '@/types/simulation'
import type { Order } from '@/types/order'
import { ROUTE_PORT_INFO } from '@/types/order'
import OrderManager from '@/components/OrderManager'
import SimAnalysisPanel from '@/components/dashboard/SimAnalysisPanel'
import { computeShipLoadStates, computeSimulationMetrics } from '@/utils/shipLoading'

// IDE 布局组件
import AppShell from '@/components/ide/AppShell'
import Workbench from '@/components/ide/Workbench'
import type { LabModule, LabModuleProps } from '@/components/ide/types'
import { ORLab, DataLab, MLLab, NotebookLab, ReportLab } from '@/components/academic'

import { loadPortsFullFromCsv } from '@/utils/csvLoader'

const CSV_PORTS = loadPortsFullFromCsv()

const PORTS_DATA = CSV_PORTS.map(p => ({
  unique_id: p.port_code,
  name: p.port_name,
  lat: p.lat,
  lon: p.lon,
  queue_length: 0,
  berth_count: 4,
  available_berths: 4,
}))

// ─── Academic Lab 模块注册 ─────────────────────────────────────

const LAB_MODULES: LabModule[] = [
  {
    id: 'or-lab',
    name: '运筹学模型',
    description: '航线配船、泊位分配、航速优化',
    category: 'or',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    component: ORLab as unknown as React.ComponentType<LabModuleProps>,
  },
  {
    id: 'ml-lab',
    name: '机器学习',
    description: '延误预测、聚类分析、异常检测',
    category: 'ml',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    component: MLLab as unknown as React.ComponentType<LabModuleProps>,
  },
  {
    id: 'data-lab',
    name: '数据浏览',
    description: '数据导入、CSV/Excel 预览、探索性分析',
    category: 'data',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
      </svg>
    ),
    component: DataLab as unknown as React.ComponentType<LabModuleProps>,
  },
  {
    id: 'notebook-lab',
    name: '学术笔记本',
    description: '统计分析、假设检验、敏感性分析',
    category: 'analysis',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
    ),
    component: NotebookLab as unknown as React.ComponentType<LabModuleProps>,
  },
  {
    id: 'report-lab',
    name: '报告生成',
    description: '自动生成科研报告与可视化图表',
    category: 'analysis',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    component: ReportLab as unknown as React.ComponentType<LabModuleProps>,
  },
]

// ─── TeachingView（教学模式） ───────────────────────────────────

function TeachingView() {
  const [activeModule, setActiveModule] = useState<string>('intro')

  const modules = [
    {
      id: 'intro',
      title: '班轮航运导论',
      icon: '🚢',
      content: [
        '班轮航运（Liner Shipping）是国际贸易的骨干运输方式，约占全球贸易量的60%。',
        'AEU（Asia-Europe Express）航线是全球最繁忙的集装箱航线之一，连接东亚、东南亚、南欧和北欧。',
        '本仿真系统采用基于Agent的离散事件仿真（Agent-based DES）范式，对AEU航线进行数字孪生建模。',
        '仿真模型包含 9 个港口、9 艘集装箱船，覆盖完整的东西向往返航线。',
      ],
      formulas: [
        { name: '准班率 (On-time Rate)', formula: 'OTR = (准时到港次数 / 总到港次数) × 100%', desc: '延误≤4小时视为准时' },
        { name: '碳排放强度 (CII)', formula: 'CII = 年CO₂排放量 / (船舶容量 × 年航行距离)', desc: 'IMO DCS 标准指标' },
      ],
    },
    {
      id: 'des',
      title: '离散事件仿真',
      icon: '⚙️',
      content: [
        '离散事件仿真（DES）是系统仿真的一种重要范式，系统状态仅在离散的时间点上发生变化。',
        '本系统使用事件驱动的仿真引擎（EventDrivenScheduler），基于最小堆（Min-Heap）事件队列。',
        '核心概念：事件（Event）、Agent（ShipAgent / PortAgent）、调度器（Scheduler）。',
        '与连续仿真不同，DES 的仿真时钟直接跳跃到下一个事件发生时刻，计算效率极高。',
      ],
      formulas: [
        { name: '航行时间', formula: 'T = D / V', desc: '距离 / 航速' },
        { name: '燃油消耗 (三次方律)', formula: 'F ∝ V³', desc: '低速航行 < 50% 经济航速时, 罚因子上调30%' },
      ],
    },
    {
      id: 'kpi',
      title: 'KPI 指标体系',
      icon: '📊',
      content: [
        '仿真模型输出多维度的关键绩效指标（KPI），从可靠性、碳排放、鲁棒性三个维度评估系统性能。',
        '可靠性维度：准班率、平均延误、延误方差、服务可靠性指数。',
        '碳排维度：总排放量、单船平均排放、每海里排放、CII 评级（A-E 五级）。',
        '鲁棒性维度：恢复时间、最大队列长度、泊位阻塞概率、系统韧性指数。',
      ],
      formulas: [
        { name: '服务可靠性指数', formula: 'SRI = OTR / (1 + D_avg/24)', desc: '综合准班率和延误的复合指标' },
        { name: '系统韧性指数', formula: 'RI = (1 - P_block) × SRF × 100', desc: 'SRF = 调度恢复因子' },
      ],
    },
    {
      id: 'experiment',
      title: '实验设计方法',
      icon: '🔬',
      content: [
        '参数扫描（Parameter Sweep）：对单一参数进行等间距采样，观察目标指标的变化规律。',
        '蒙特卡洛分析（Monte Carlo）：引入随机种子，对不确定性因素进行多次重复仿真。',
        'What-if 场景对比：预设多种政策/环境场景（如港口拥堵、碳税、CII严格监管），对比系统响应。',
        '统计显著性检验：通过 t 检验和 ANOVA 判断不同场景之间的差异是否统计显著。',
      ],
      formulas: [
        { name: 'Cohen\'s d 效应量', formula: 'd = (μ₁ - μ₂) / σ_pooled', desc: 'd ≥ 0.8 为大效应' },
        { name: '弹性分析', formula: 'ε = (ΔM/M) / (ΔP/P)', desc: '指标对参数的敏感度' },
      ],
    },
    {
      id: 'carbon',
      title: '环境合规',
      icon: '🌱',
      content: [
        'IMO（国际海事组织）设定了航运业的减排目标：到 2050 年温室气体排放减少 50%。',
        '碳排放强度（CII）是 IMO DCS 框架下的指标之一，此外还有 ECA（排放控制区）的燃油切换规则。',
        '本系统模拟了 ECA 区域的燃油切换行为：进入 ECA 区域自动切换为 MGO（低硫油）。',
        '环境合规是船舶运营的约束条件之一，运营决策需在准班率、燃油成本和环境合规之间取得平衡。',
      ],
      formulas: [
        { name: 'CO₂排放率', formula: 'E_CO₂ = F × EF', desc: 'F = 小时油耗, EF = CO₂因子 (VLSFO: 3.114, MGO: 3.206)' },
        { name: 'CII 评级', formula: 'A ≤ 0.85R, B ≤ 1.00R, C ≤ 1.15R, D ≤ 1.35R', desc: 'R = 参考CII值' },
      ],
    },
  ]

  const currentModule = modules.find(m => m.id === activeModule) || modules[0]

  return (
    <div className="h-full overflow-auto bg-[#0a1929]">
      <div className="max-w-7xl mx-auto p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white mb-2">AI 教学中心</h1>
          <p className="text-gray-400">班轮航运仿真学术知识体系</p>
        </div>

        {/* 模块导航 */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {modules.map((mod) => (
            <button
              key={mod.id}
              onClick={() => setActiveModule(mod.id)}
              className={`
                flex items-center gap-2 px-4 py-3 rounded-lg whitespace-nowrap transition-all
                ${activeModule === mod.id
                  ? 'bg-marine-500/20 text-marine-400 border border-marine-500/30'
                  : 'bg-white/5 text-gray-400 hover:text-white border border-transparent'
                }
              `}
            >
              <span className="text-lg">{mod.icon}</span>
              <span className="font-medium text-sm">{mod.title}</span>
            </button>
          ))}
        </div>

        {/* 内容区域 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <Card className="p-5">
              <h2 className="text-lg font-semibold text-white mb-4">{currentModule.title}</h2>
              <div className="space-y-3">
                {currentModule.content.map((para, idx) => (
                  <p key={idx} className="text-gray-300 text-sm leading-relaxed">{para}</p>
                ))}
              </div>
            </Card>

            {currentModule.formulas.length > 0 && (
              <Card className="p-5">
                <h3 className="text-sm font-medium text-gray-300 mb-3">核心公式</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {currentModule.formulas.map((f, idx) => (
                    <div key={idx} className="bg-white/5 rounded-lg p-4 border border-white/10">
                      <div className="text-xs text-gray-500 mb-1">{f.name}</div>
                      <div className="text-sm font-mono text-marine-300 mb-1">{f.formula}</div>
                      <div className="text-[11px] text-gray-500">{f.desc}</div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>

          <div className="space-y-4">
            <Card className="p-5">
              <h3 className="text-sm font-medium text-white mb-3">🏷️ 关键概念</h3>
              <div className="flex flex-wrap gap-2">
                {[
                  'Agent-based DES', 'Event-driven', 'ECA Zone',
                  'M/M/c Queue', 'Monte Carlo', 'Parameter Sweep', 'Hypothesis Test',
                  'Effect Size', 'Sensitivity Analysis', 'Multi-objective',
                ].map((tag) => (
                  <span key={tag} className="px-2.5 py-1 text-xs rounded-full bg-white/5 text-gray-400 border border-white/10">
                    {tag}
                  </span>
                ))}
              </div>
            </Card>

            <Card className="p-5">
              <h3 className="text-sm font-medium text-white mb-3">📚 推荐文献</h3>
              <div className="space-y-2">
                <div className="text-xs text-gray-400 border-b border-white/5 pb-2">
                  <span className="text-gray-500">IMO MEPC.308(73)</span> — CO₂排放因子标准
                </div>
                <div className="text-xs text-gray-400 border-b border-white/5 pb-2">
                  <span className="text-gray-500">Sea-Intelligence 2024</span> — 全球班轮准班率报告
                </div>
                <div className="text-xs text-gray-400 border-b border-white/5 pb-2">
                  <span className="text-gray-500">UNCTAD 2024</span> — 海运回顾
                </div>
                <div className="text-xs text-gray-400 border-b border-white/5 pb-2">
                  <span className="text-gray-500">Zeigler et al.</span> — DEVS 形式化建模
                </div>
                <div className="text-xs text-gray-400">
                  <span className="text-gray-500">Law & Kelton</span> — 仿真建模与分析
                </div>
              </div>
            </Card>

            <Card className="p-5">
              <h3 className="text-sm font-medium text-white mb-3">📝 学习检查</h3>
              <div className="text-xs text-gray-400 space-y-2">
                <p>1. DES 和连续仿真的本质区别是什么？</p>
                <p>2. CII 评级 A-E 的阈值分别是什么？</p>
                <p>3. 如何用排队论验证港口模型的准确性？</p>
                <p>4. Cohen's d 大于多少可以认为是大效应？</p>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── 简化的 MonitorView（纯地图 + 浮动覆盖层） ────────────────

function MonitorView({
  displayState,
  selectedShip,
  setSelectedShip,
  selectedPort,
  setSelectedPort,
  currentTime,
  ships,
  simulationMode,
  mapType,
  onViewDetail,
  onStart,
  trajectories,
  cesiumSimTime,
  onSimTimeUpdate,
  shipLoadStates,
}: {
  displayState: SimState | null
  selectedShip: string | null
  setSelectedShip: (id: string | null) => void
  selectedPort: string | null
  setSelectedPort: (id: string | null) => void
  currentTime: number
  ships: ShipData[]
  simulationMode: string
  mapType: '3d' | '2d'
  onViewDetail?: (type: string, id: string) => void
  onStart?: () => void
  trajectories?: Record<string, ShipTrajectoryData> | null
  cesiumSimTime?: number
  onSimTimeUpdate?: (simHours: number) => void
  shipLoadStates?: any[]
}) {
  const [simStarted, setSimStarted] = useState(false)
  const ports = (displayState?.ports ?? {}) as Record<string, PortData>
  const isRealTime = simulationMode === 'real_time'

  // 实时模式自动标记为已启动
  useEffect(() => {
    if (isRealTime) setSimStarted(true)
  }, [isRealTime])

  const isRunning = displayState?.is_running ?? false

  return (
    <div className="h-full relative">
      {/* 仿真未启动时的覆盖层 */}
      {!isRealTime && !isRunning && !simStarted && (
        <SimNotStarted
          onStart={() => {
            setSimStarted(true)
            onStart?.()
          }}
        />
      )}

      {/* 地图 */}
      <MapContainer
        ships={ships}
        ports={PORTS_DATA.map(p => ({
          ...p,
          queue_length: ports[p.unique_id]?.queue_length ?? 0,
          available_berths: ports[p.unique_id]?.available_berths ?? p.available_berths,
        }))}
        selectedShipId={selectedShip}
        onShipClick={(shipId: string) => { setSelectedShip(shipId); setSelectedPort(null) }}
        onPortClick={(portId: string) => { setSelectedPort(portId); setSelectedShip(null) }}
        simulationMode={simulationMode}
        mapType={mapType}
        trajectories={trajectories}
        currentTime={currentTime}
        isRunning={displayState?.is_running ?? false}
        speed={displayState?.speed ?? 60}
        onSimTimeUpdate={onSimTimeUpdate}
      />

      {/* 选中船舶详情 */}
      {selectedShip && (
        <div className="absolute top-4 left-4 z-20 w-80">
          <ShipDetailAnimation
            ship={{
              ...(displayState?.ships?.[selectedShip] ?? {}) as ShipData,
              currentLoadTEU: shipLoadStates?.find(s => s.shipID === selectedShip)?.currentLoadTEU,
              maxCapacityTEU: shipLoadStates?.find(s => s.shipID === selectedShip)?.maxCapacityTEU,
              deliveredRevenue: shipLoadStates?.find(s => s.shipID === selectedShip)?.deliveredRevenue,
            }}
            onClose={() => setSelectedShip(null)}
            onViewDetail={() => onViewDetail?.('ship', selectedShip)}
          />
        </div>
      )}

      {/* 选中港口详情 */}
      {selectedPort && !selectedShip && (
        <div className="absolute top-4 left-4 z-20 w-80">
          <PortMicroView
            port={{
              ...PORTS_DATA.find(p => p.unique_id === selectedPort)!,
              queue_length: ports[selectedPort]?.queue_length ?? 0,
              available_berths: ports[selectedPort]?.available_berths ?? PORTS_DATA.find(p => p.unique_id === selectedPort)!.available_berths,
              waiting_queue: (ports[selectedPort]?.waiting_queue ?? []) as string[],
            }}
            onClose={() => setSelectedPort(null)}
            onViewDetail={() => onViewDetail?.('port', selectedPort)}
          />
        </div>
      )}
    </div>
  )
}

// ─── AnalysisView（数据分析视图） ──────────────────────────────

function AnalysisView({ displayState, ships, simMetrics, shipLoadStates }: { displayState: SimState | null; ships: ShipData[]; simMetrics?: any; shipLoadStates?: any[] }) {
  const [kpiData, setKpiData] = useState<KpiData | null>(null)
  const [trendData, setTrendData] = useState<TrendDataPoint[]>([])
  const simTime = displayState?.current_time ?? 0

  useEffect(() => {
    const fetchKPI = async () => {
      try {
        const res = await fetch('/api/kpi/dashboard')
        if (res.ok) {
          const data = await res.json()
          setKpiData(data)
        }
      } catch (e) {
        console.error('Failed to fetch KPI:', e)
      }
    }
    const fetchTrend = async () => {
      try {
        const res = await fetch('/api/kpi/trend')
        if (res.ok) {
          const data = await res.json()
          setTrendData(data.trend || [])
        }
      } catch (e) {
        console.error('Failed to fetch trend:', e)
      }
    }
    fetchKPI()
    fetchTrend()
    const interval = setInterval(() => { fetchKPI(); fetchTrend() }, 5000)
    return () => clearInterval(interval)
  }, [])

  const avgUtilization = (() => {
    if (!displayState?.ports) return 0
    const ports = Object.values(displayState.ports) as PortData[]
    if (ports.length === 0) return 0
    const totalUtil = ports.reduce((sum: number, p: PortData) => {
      const total = p.berth_count || 4
      const used = total - (p.available_berths ?? total)
      return sum + (used / total) * 100
    }, 0)
    return totalUtil / ports.length
  })()

  const ganttData = ships.map((ship: ShipData) => ({
    ship_id: ship.unique_id,
    name: ship.name,
    segments: [
      {
        start_time: Math.max(0, simTime - 168),
        end_time: simTime,
        state: ship.state || 'IDLE',
        port: ship.current_port || undefined,
      },
    ],
  }))

  const routeOrder = ['SHA', 'NGB', 'XMN', 'HKG', 'SZX', 'SIN', 'PIR', 'RTM', 'HAM']
  const portsMap = Object.fromEntries(
    routeOrder.map(id => [id, (displayState?.ports ?? {})[id]]).filter(([_, p]) => p)
  )
  const delayNodes = (Object.entries(portsMap) as [string, PortData][]).map(([id, p]) => ({
    id,
    name: PORTS_DATA.find(pd => pd.unique_id === id)?.name || id,
    avg_delay: (p.queue_length || 0) * 2.5,
    ship_count: p.queue_length || 0,
    is_congested: (p.queue_length || 0) > 2,
  }))
  const delayLinks: Array<{source: string; target: string; delay_hours: number; propagation_count: number}> = []
  for (let i = 0; i < routeOrder.length - 1; i++) {
    const source = portsMap[routeOrder[i]]
    const target = portsMap[routeOrder[i + 1]]
    if (source && target && (source.queue_length || 0) > 0 && (target.queue_length || 0) > 0) {
      delayLinks.push({
        source: routeOrder[i],
        target: routeOrder[i + 1],
        delay_hours: (source.queue_length || 0) * 2.5,
        propagation_count: Math.max(1, Math.round((source.queue_length || 0) / 2)),
      })
    }
  }

  const trendChartOption = {
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: 'rgba(10, 25, 47, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff', fontSize: 12 },
    },
    legend: {
      data: ['准班率', '碳排放'],
      textStyle: { color: '#9CA3AF', fontSize: 11 },
      top: 0,
    },
    grid: { top: 28, right: 12, bottom: 20, left: 45 },
    xAxis: {
      type: 'category' as const,
      data: trendData.map((_: TrendDataPoint, i: number) => `T${i + 1}`),
      axisLine: { lineStyle: { color: '#4B5563' } },
      axisLabel: { color: '#9CA3AF', fontSize: 10 },
    },
    yAxis: {
      type: 'value' as const,
      axisLine: { lineStyle: { color: '#4B5563' } },
      axisLabel: { color: '#9CA3AF', fontSize: 10 },
      splitLine: { lineStyle: { color: '#374151' } },
    },
    series: [
      {
        name: '准班率',
        type: 'line' as const,
        data: trendData.map((d: TrendDataPoint) => d.on_time_rate),
        smooth: true,
        lineStyle: { color: '#3B82F6', width: 2 },
        areaStyle: { color: 'rgba(59,130,246,0.1)' },
        symbol: 'circle' as const,
        symbolSize: 4,
      },
      {
        name: '碳排放',
        type: 'line' as const,
        data: trendData.map((d: TrendDataPoint) => d.carbon_total),
        smooth: true,
        lineStyle: { color: '#10B981', width: 2 },
        areaStyle: { color: 'rgba(16,185,129,0.1)' },
        symbol: 'circle' as const,
        symbolSize: 4,
      },
    ],
  }

  return (
    <div className="h-full overflow-auto p-4 bg-[#0a1929]">
      {simMetrics ? (
        <SimAnalysisPanel
          totalRevenue={simMetrics.totalRevenue}
          averageUtilization={simMetrics.averageUtilization}
          globalDelayRate={simMetrics.globalDelayRate}
          revenueTimeline={simMetrics.revenueTimeline}
          shipCount={shipLoadStates?.length ?? ships.length}
        />
      ) : (
        <div className="text-center text-gray-500 p-8">加载中...</div>
      )}
    </div>
  )
}

// ─── HomePage ──────────────────────────────────────────────────

export default function HomePage() {
  const [selectedShip, setSelectedShip] = useState<string | null>(null)
  const [selectedPort, setSelectedPort] = useState<string | null>(null)
  const [displayState, setDisplayState] = useState<SimState | null>(null)
  const [aiDecisions, setAIDecisions] = useState<AIDecision[]>([])
  const decisionLogTrackerRef = useRef<Record<string, number>>({})
  const [showAIChat, setShowAIChat] = useState(false)
  const [simulationMode, setSimulationMode] = useState('academic')
  const [fullScreenView, setFullScreenView] = useState<{
    type: 'ship' | 'port'
    id: string
  } | null>(null)

  const [orders, setOrders] = useState<Order[]>(() => {
    try {
      const saved = typeof window !== 'undefined' && localStorage.getItem('shipping_orders_week1')
      if (saved) return JSON.parse(saved) as Order[]
    } catch {}
    return []
  })
  const [showOrderManager, setShowOrderManager] = useState(false)

  // AppShell 状态
  const [mapType, setMapType] = useState<'3d' | '2d'>('3d')
  const [resultView, setResultView] = useState<{ title: string; content: ReactNode } | null>(null)

  const handleStateChange = useCallback((state: SimState) => {
    setDisplayState(state)
    if (state.simulation_mode) {
      setSimulationMode(state.simulation_mode)
    }
    // 提取新的 AI 决策日志
    if (state.ships) {
      const newEntries: AIDecision[] = []
      Object.entries(state.ships).forEach(([shipId, ship]: [string, ShipData]) => {
        if (!ship || !Array.isArray(ship.decision_log)) return
        const prevLen = decisionLogTrackerRef.current[shipId] ?? 0
        const currentLen = ship.decision_log.length
        if (currentLen > prevLen) {
          for (let i = prevLen; i < currentLen; i++) {
            const entry = ship.decision_log[i] as Record<string, unknown> | undefined
            if (entry) {
              newEntries.push({
                _id: `${shipId}-${i}`,
                ship_id: shipId,
                ship_name: ship.name || shipId,
                event: (entry.event as string) || 'decision',
                ...entry,
              } as AIDecision)
            }
          }
          decisionLogTrackerRef.current[shipId] = currentLen
        }
      })
      if (newEntries.length > 0) {
        setAIDecisions(prev => {
          const combined = [...prev, ...newEntries]
          return combined.slice(-200)
        })
      }
    }
  }, [])

  const {
    connected,
    simState,
    trajectories,
    start,
    pause,
    setSpeed,
    reset,
    setMode: wsSetMode,
    setAisSource,
    getState,
  } = useWebSocket(handleStateChange)

  const [localSpeed, setLocalSpeed] = useState(60)
  const [cesiumSimTime, setCesiumSimTime] = useState(0)

  const handleSimTimeUpdate = useCallback((simHours: number) => {
    setCesiumSimTime(simHours)
  }, [])

  const handleSetMode = useCallback((mode: string) => {
    setSimulationMode(mode)
    wsSetMode(mode)
  }, [wsSetMode])

  useEffect(() => {
    if (connected) {
      getState()
    }
  }, [connected, getState])

  useEffect(() => {
    if (displayState?.speed) setLocalSpeed(displayState.speed)
  }, [displayState?.is_running, displayState?.speed])

  const handleSpeedChange = (newSpeed: number) => {
    setLocalSpeed(newSpeed)
    setSpeed(newSpeed)
  }

  const ships = Object.values(displayState?.ships ?? {})
  const isRunning = displayState?.is_running ?? false
  const currentTime = displayState?.current_time ?? 0
  const speed = localSpeed
  const aisSourceMode = displayState?.ais_source_mode ?? 'mock'

  const simTimeForMetrics = cesiumSimTime > 0 ? cesiumSimTime : currentTime
  const shipLoadStates = computeShipLoadStates(orders, simTimeForMetrics)
  const simMetrics = computeSimulationMetrics(orders, shipLoadStates, simTimeForMetrics)

  const handleNavigate = (targetType: string, targetId: string) => {
    if (targetType === 'ship') {
      setSelectedShip(targetId)
    } else if (targetType === 'port') {
      setSelectedPort(targetId)
    }
  }

  const handleStart = useCallback(() => {
    start(speed)
  }, [start, speed])

  return (
    <>
      <AppShell
        // Activity Bar
        activityItems={[
          {
            id: 'config',
            icon: (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            ),
            label: '仿真配置',
          },
          {
            id: 'lab',
            icon: (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
            ),
            label: '实验台',
          },
          {
            id: 'orders',
            icon: (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            ),
            label: '订单管理',
          },
        ]}
        // 左侧侧边栏面板
        sidebarPanels={{
          config: (
            <SimulationConfig
              connected={connected}
              isRunning={isRunning}
              speed={speed}
              onReset={reset}
              onApplyConfig={async (config) => {
                const res = await fetch('/api/sim/config', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(config),
                })
                if (!res.ok) throw new Error('配置应用失败')
                // 重新获取状态
                getState()
              }}
            />
          ),
          lab: (
            <Workbench
              modules={LAB_MODULES}
              onOpenResult={(title, content) => setResultView({ title, content })}
            />
          ),
          orders: (
            <OrderManager orders={orders} onOrdersChange={(newOrders) => {
              setOrders(newOrders);
              try { localStorage.setItem('shipping_orders_week1', JSON.stringify(newOrders)) } catch {}
            }} />
          ),
        }}
        // 工作区标签页
        workspaceViews={[
          {
            id: 'map',
            label: '地图',
            icon: (
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
              </svg>
            ),
            component: (
              <MonitorView
                displayState={displayState}
                selectedShip={selectedShip}
                setSelectedShip={setSelectedShip}
                selectedPort={selectedPort}
                setSelectedPort={setSelectedPort}
currentTime={cesiumSimTime > 0 ? cesiumSimTime : currentTime}
        ships={ships}
                simulationMode={simulationMode}
                mapType={mapType}
                trajectories={trajectories}
                onViewDetail={(type, id) => setFullScreenView({ type: type as 'ship' | 'port', id })}
                onStart={handleStart}
                cesiumSimTime={cesiumSimTime}
                onSimTimeUpdate={handleSimTimeUpdate}
                shipLoadStates={shipLoadStates}
              />
            ),
          },
          {
            id: 'analysis',
            label: '分析',
            icon: (
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            ),
            component: <AnalysisView displayState={displayState} ships={ships} simMetrics={simMetrics} shipLoadStates={shipLoadStates} />,
          },
          {
            id: 'teaching',
            label: '教学',
            icon: (
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            ),
            component: <TeachingView />,
          },
        ]}
        // 右侧侧边栏（AI 对话）
        rightSidebarOpen={showAIChat}
        rightSidebar={
          showAIChat ? (
            <AIChatPanel
              isOpen={showAIChat}
              onClose={() => setShowAIChat(false)}
              onNavigate={handleNavigate}
              aiDecisions={aiDecisions}
              onClearDecisions={handleClearDecisions}
              sidebarMode
            />
          ) : undefined
        }
        onRightSidebarClose={() => {
          setShowAIChat(false)
        }}
        // 工作区标题栏插槽：控制面板中间，AI 按钮右侧
        headerCenter={
          <ControlPanel
            isRunning={isRunning}
            currentTime={cesiumSimTime > 0 ? cesiumSimTime : currentTime}
            speed={speed}
            simulationMode={simulationMode}
            onStart={handleStart}
            onPause={pause}
            onReset={reset}
            onSpeedChange={handleSpeedChange}
            mapType={mapType}
            onMapTypeChange={setMapType}
            connected={connected}
            onSetMode={handleSetMode}
            hideAnalysis
          />
        }
        headerRight={
          <button
            onClick={() => setShowAIChat(!showAIChat)}
            className={`p-1.5 rounded-md transition-all ${
              showAIChat
                ? 'text-marine-400 bg-marine-500/20'
                : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
            }`}
            title="AI 助手"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </button>
        }
      />

      {/* ─── 全局浮动覆盖层 ─── */}

      {/* 全屏详细视图 */}
      {fullScreenView && (() => {
        if (fullScreenView.type === 'ship') {
          const shipData = displayState?.ships?.[fullScreenView.id]
          if (!shipData?.unique_id) return null
          return (
            <FullScreenDetailView
              type="ship"
              data={shipData}
              onClose={() => setFullScreenView(null)}
            />
          )
        }
        const portData = PORTS_DATA.find(p => p.unique_id === fullScreenView.id)
        if (!portData) return null
        const portState = displayState?.ports?.[fullScreenView.id]
        return (
          <FullScreenDetailView
            type="port"
            data={{
              ...portData,
              queue_length: portState?.queue_length ?? portData.queue_length,
              available_berths: portState?.available_berths ?? portData.available_berths,
              waiting_queue: (portState?.waiting_queue ?? []) as string[],
            }}
            onClose={() => setFullScreenView(null)}
          />
        )
      })()}

      {/* 学术模块结果浮动窗口 */}
      {resultView && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-[#0d1e30] border border-white/10 rounded-xl shadow-2xl shadow-black/50 max-w-xl w-full mx-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
              <h3 className="text-sm font-medium text-gray-200">{resultView.title}</h3>
              <button
                onClick={() => setResultView(null)}
                className="p-1 text-gray-500 hover:text-white hover:bg-white/10 rounded transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {resultView.content}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
