export interface Order {
  orderID: string
  originPort: string
  destPort: string
  revenuePerTEU: number
  volumeTEU: number
  routeID: string
  week: number
  deadline: number
}

export interface RoutePortInfo {
  routeID: string
  ports: string[]
  cycleDays: number
  cycleWeeks: number
  portNames: Record<string, string>
  shipCapacity: number
}

export const ROUTE_PORT_INFO: RoutePortInfo[] = [
  {
    routeID: 'AEU1',
    ports: ['CNTAO', 'CNSHA', 'CNNGB', 'CNXMN', 'CNYTN', 'SGSIN', 'GBFXT', 'BEZEE', 'PLGDY', 'DEWVN'],
    cycleDays: 105,
    cycleWeeks: 15,
    portNames: { CNTAO: '青岛', CNSHA: '上海', CNNGB: '宁波', CNXMN: '厦门', CNYTN: '盐田', SGSIN: '新加坡', GBFXT: '费利克斯托', BEZEE: '泽布吕赫', PLGDY: '格但斯克', DEWVN: '威廉港' },
    shipCapacity: 21413,
  },
  {
    routeID: 'AEU2',
    ports: ['CNNGB', 'CNSHA', 'CNYTN', 'SGSIN', 'MAPTM', 'FRDKK', 'GBSOU', 'FRLEH', 'MYPKG'],
    cycleDays: 105,
    cycleWeeks: 15,
    portNames: { CNNGB: '宁波', CNSHA: '上海', CNYTN: '盐田', SGSIN: '新加坡', MAPTM: '丹吉尔', FRDKK: '敦刻尔克', GBSOU: '南安普顿', FRLEH: '勒阿弗尔', MYPKG: '巴生港' },
    shipCapacity: 16000,
  },
  {
    routeID: 'AEU3',
    ports: ['CNTXG', 'CNDLC', 'CNTAO', 'CNSHA', 'CNNGB', 'SGSIN', 'NLRTM', 'DEHAM', 'BEANR'],
    cycleDays: 98,
    cycleWeeks: 14,
    portNames: { CNTXG: '天津', CNDLC: '大连', CNTAO: '青岛', CNSHA: '上海', CNNGB: '宁波', SGSIN: '新加坡', NLRTM: '鹿特丹', DEHAM: '汉堡', BEANR: '安特卫普' },
    shipCapacity: 19100,
  },
]

export const CYCLE_PORT_SEQUENCE: Record<string, string[]> = {
  AEU1: ['CNTAO', 'CNSHA', 'CNNGB', 'CNXMN', 'CNYTN', 'SGSIN', 'GBFXT', 'BEZEE', 'PLGDY', 'DEWVN', 'SGSIN', 'CNYTN', 'CNTAO'],
  AEU2: ['CNNGB', 'CNSHA', 'CNYTN', 'SGSIN', 'MAPTM', 'FRDKK', 'GBSOU', 'FRLEH', 'MYPKG', 'CNNGB'],
  AEU3: ['CNTXG', 'CNDLC', 'CNTAO', 'CNSHA', 'CNNGB', 'SGSIN', 'NLRTM', 'DEHAM', 'BEANR', 'CNSHA', 'CNTXG'],
}

export interface ShipLoadState {
  shipID: string
  shipName: string
  routeID: string
  weekOffset: number
  currentLoadTEU: number
  maxCapacityTEU: number
  pickedOrders: Order[]
  orderPickupTimes: Record<string, number>
  delayedOrderIDs: string[]
  deliveredRevenue: number
  currentPort: string
  legHistory: LegRecord[]
}

export interface LegRecord {
  fromPort: string
  toPort: string
  loadAtDeparture: number
  pickedUp: number
  delivered: number
  revenueEarned: number
}

export interface SimulationMetrics {
  totalRevenue: number
  averageUtilization: number
  globalDelayRate: number
  revenueTimeline: { time: number; revenue: number }[]
  routeRevenue: Record<string, { total: number; average: number }>
  totalAverageRevenue: number
  routeRevenueTimeline: Record<string, { time: number; revenue: number }[]>
}

export interface PortBufferItem {
  orderID: string
  originPort: string
  destPort: string
  revenuePerTEU: number
  volumeTEU: number
  routeID: string
  week: number
  deadline: number
  remainingTEU: number
}

export interface AllocationPlan {
  orderID: string
  targetRoute: string
  targetAbsWeek: number
  allocatedVolume: number
  transitHours: number
}

export interface CommittedSlot {
  routeID: string
  absWeek: number
  allocatedVolume: number
}