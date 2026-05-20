// 共享类型定义 — 仿真状态、AI 决策、图表数据等

// 从 useWebSocket 复用的类型引用
export interface SimState {
  current_time: number
  is_running: boolean
  speed: number
  simulation_mode?: string
  ais_source_mode?: string
  ships: Record<string, ShipData>
  ports: Record<string, PortData>
}

export interface ShipData {
  unique_id: string
  name: string
  state: string
  current_speed: number
  lat: number | null
  lon: number | null
  current_port: string | null
  next_port: string | null
  service?: string
  viz_status?: string
  co2_emissions?: number
  decision_log?: unknown[]
  cii_rating?: string
  cumulative_delay?: number
}

export interface PortData {
  unique_id: string
  name: string
  lat: number
  lon: number
  queue_length: number
  available_berths?: number
  berth_count?: number
  waiting_queue?: unknown[]
}

// AI 决策记录
export interface AIDecision {
  _id: string
  ship_id: string
  ship_name: string
  event: string
  sim_time?: number
  reason?: string
  summary?: string
  decision?: string
  context?: Record<string, number | string>
}

// 趋势数据点
export interface TrendDataPoint {
  sim_time: number
  on_time_rate: number
  carbon_total: number
  avg_delay: number
}

// KPI 数据
export interface KpiData {
  on_time_rate: number
  avg_utilization: number
  total_co2: number
  carbon_total?: number
  avg_cii_ratio: number
}

// 蒙特卡洛仿真的单次运行结果
export interface IndividualRun {
  on_time_rate: number
  avg_delay: number
  total_co2: number
}

export interface SummaryStats {
  mean?: number
  std?: number
  p5?: number
  p25?: number
  p50?: number
  p75?: number
  p95?: number
}

export interface MonteCarloResult {
  individual_runs: IndividualRun[]
  summary?: {
    on_time_rate?: SummaryStats
    total_carbon?: SummaryStats
    avg_delay?: SummaryStats
  }
}

// 碳排放对比数据点
export interface CarbonDataPoint {
  ship_name: string
  total_co2: number
  cii_rating?: string
}

// 统计数据
export interface HistogramBin {
  range: string
  count: number
  bin_start?: number
  bin_end?: number
}

export interface DelayPerShip {
  histogram: HistogramBin[]
  boxplot?: { min: number; q1: number; median: number; q3: number; max: number }
}

export interface DescriptiveStats {
  mean: number
  max: number
  variance: number
  ci_lower_95?: number
  ci_upper_95?: number
}

export interface StatsData {
  delay_analysis: {
    per_ship: DelayPerShip
    descriptive: DescriptiveStats
  }
  state_distribution?: Record<string, number>
  on_time_rate_trend?: {
    descriptive?: DescriptiveStats
  }
  normality?: {
    delays?: { p_value: number }
  }
  port_queues?: Record<string, number>
  ships_tracked?: number
  snapshots_count?: number
  carbon_analysis?: {
    total?: number
  }
}

// 报告用 KPI 快照
export interface ReportKpiData {
  reliability?: {
    on_time_rate: number
    mean_delay: number
    max_delay: number
    delay_variance: number
    service_reliability_index: number
  }
  carbon?: {
    total_emissions: number
    per_ship_average: number
    per_nautical_mile: number
    operational_emissions: number
    maneuvering_emissions: number
  }
  robustness?: {
    recovery_time: number
    max_queue_length: number
    berth_blocking_probability: number
    schedule_recovery_factor: number
    system_resilience_index: number
  }
}
