// 集中式 API 端点常量

const BASE = ''

export const API = {
  // 仿真控制
  SIM_STATE: `${BASE}/api/sim/state`,
  SIM_START: `${BASE}/api/sim/start`,
  SIM_STOP: `${BASE}/api/sim/stop`,
  SIM_STEP: `${BASE}/api/sim/step`,
  SIM_RESET: `${BASE}/api/sim/reset`,
  SIM_SPEED: `${BASE}/api/sim/speed`,
  SIM_MODE: `${BASE}/api/sim/mode`,

  // KPI & 统计
  KPI: `${BASE}/api/kpi`,
  STATISTICS: `${BASE}/api/statistics`,
  CARBON_DATA: `${BASE}/api/carbon/data`,

  // 实验
  EXPERIMENT_SWEEP: `${BASE}/api/experiment/sweep`,
  EXPERIMENT_MONTE_CARLO: `${BASE}/api/experiment/monte-carlo`,
  EXPERIMENT_LIST: `${BASE}/api/experiment/list`,
  EXPERIMENT_RUN: `${BASE}/api/experiment/run`,

  // 学术实验室
  ACADEMIC_DATASETS: `${BASE}/api/academic-lab/datasets`,
  ACADEMIC_DATASET: (id: string) => `${BASE}/api/academic-lab/datasets/${id}`,
  ACADEMIC_DATASET_IMPORT: (id: string) => `${BASE}/api/academic-lab/datasets/${id}/import`,
  ACADEMIC_DATASET_UPLOAD: `${BASE}/api/academic-lab/datasets/upload`,
  ACADEMIC_ML_TRAIN: `${BASE}/api/academic-lab/ml/train`,
  ACADEMIC_ML_PREDICT: `${BASE}/api/academic-lab/ml/predict`,
  ACADEMIC_OR_SOLVE: `${BASE}/api/academic-lab/or/solve`,

  // AI
  AI_CHAT: `${BASE}/api/ai/chat`,
  AI_DECISIONS: `${BASE}/api/ai/decisions`,
  AI_AGENTS: `${BASE}/api/ai/agents`,
  AI_AGENT_CONFIG: (id: string) => `${BASE}/api/ai/agents/${id}`,

  // WebSocket
  WS: `ws://localhost:8000/ws`,
} as const

// CDN 资源
export const CDN = {
  LEAFLET_CSS: 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  LEAFLET_JS: 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  CARTO_DARK_TILES: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
} as const
