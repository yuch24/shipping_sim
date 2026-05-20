import type { Order, RoutePortInfo, ShipLoadState, LegRecord, SimulationMetrics } from '@/types/order'
import { ROUTE_PORT_INFO } from '@/types/order'

const ROUTE_SCHEDULES_HOURS: Record<string, { port: string; eta: number; etd: number | null }[]> = {
  AEU1: [
    { port: 'CNTAO', eta: 0, etd: 24 },
    { port: 'CNSHA', eta: 72, etd: 96 },
    { port: 'CNNGB', eta: 120, etd: 144 },
    { port: 'CNXMN', eta: 192, etd: 216 },
    { port: 'CNYTN', eta: 240, etd: 264 },
    { port: 'SGSIN', eta: 336, etd: 360 },
    { port: 'GBFXT', eta: 1080, etd: 1104 },
    { port: 'BEZEE', eta: 1152, etd: 1176 },
    { port: 'PLGDY', eta: 1248, etd: 1272 },
    { port: 'DEWVN', eta: 1392, etd: 1416 },
    { port: 'SGSIN', eta: 2280, etd: 2304 },
    { port: 'CNYTN', eta: 2400, etd: 2424 },
    { port: 'CNTAO', eta: 2520, etd: null },
  ],
  AEU2: [
    { port: 'CNNGB', eta: 0, etd: 24 },
    { port: 'CNSHA', eta: 72, etd: 96 },
    { port: 'CNYTN', eta: 144, etd: 168 },
    { port: 'SGSIN', eta: 264, etd: 288 },
    { port: 'MAPTM', eta: 864, etd: 888 },
    { port: 'FRDKK', eta: 984, etd: 1008 },
    { port: 'GBSOU', eta: 1056, etd: 1080 },
    { port: 'FRLEH', eta: 1320, etd: 1344 },
    { port: 'MYPKG', eta: 2280, etd: 2304 },
    { port: 'CNNGB', eta: 2520, etd: null },
  ],
  AEU3: [
    { port: 'CNTXG', eta: 0, etd: 24 },
    { port: 'CNDLC', eta: 72, etd: 96 },
    { port: 'CNTAO', eta: 120, etd: 144 },
    { port: 'CNSHA', eta: 192, etd: 216 },
    { port: 'CNNGB', eta: 240, etd: 264 },
    { port: 'SGSIN', eta: 384, etd: 408 },
    { port: 'NLRTM', eta: 1104, etd: 1128 },
    { port: 'DEHAM', eta: 1200, etd: 1224 },
    { port: 'BEANR', eta: 1296, etd: 1320 },
    { port: 'CNSHA', eta: 2280, etd: 2304 },
    { port: 'CNTXG', eta: 2352, etd: null },
  ],
}

function getRouteInfo(routeID: string): RoutePortInfo | undefined {
  return ROUTE_PORT_INFO.find(r => r.routeID === routeID)
}

export function computeShipLoadStates(
  orders: Order[],
  simTimeHours: number,
): ShipLoadState[] {
  const result: ShipLoadState[] = []

  for (const routeInfo of ROUTE_PORT_INFO) {
    const schedule = ROUTE_SCHEDULES_HOURS[routeInfo.routeID]
    if (!schedule) continue

    const cycleHours = schedule[schedule.length - 1].eta
    const numShips = routeInfo.cycleWeeks

    for (let weekIdx = 0; weekIdx < numShips; weekIdx++) {
      const offset = weekIdx * 168
      const shipID = `${routeInfo.routeID}_s${String(weekIdx + 1).padStart(3, '0')}`
      const shipName = `${routeInfo.routeID} Ship ${weekIdx + 1}`

      if (simTimeHours < offset) {
        result.push({
          shipID, shipName, routeID: routeInfo.routeID, weekOffset: weekIdx,
          currentLoadTEU: 0, maxCapacityTEU: routeInfo.shipCapacity,
          pickedOrders: [], deliveredRevenue: 0,
          currentPort: schedule[0].port, legHistory: [],
        })
        continue
      }

      const cyclePos = (simTimeHours - offset) % cycleHours
      const absTime = offset + cyclePos

      let currentPortIdx = 0
      for (let i = 0; i < schedule.length; i++) {
        if (absTime >= schedule[i].eta) {
          currentPortIdx = i
        }
      }

      const currentPort = schedule[currentPortIdx].port
      let currentLoad = 0
      let deliveredRevenue = 0
      const pickedOrders: Order[] = []
      const legHistory: LegRecord[] = []

      const routeOrders = orders.filter(o => o.routeID === routeInfo.routeID)

      for (let portIdx = 0; portIdx <= currentPortIdx; portIdx++) {
        const portCode = schedule[portIdx].port
        const portAbsTime = offset + schedule[portIdx].eta

        const ordersHere = routeOrders.filter(o => {
          if (o.originPort === portCode) {
            const orderWeek = Math.floor(o.deadline / 168)
            return orderWeek === weekIdx || (portIdx === 0 && o.deadline <= portAbsTime)
          }
          return false
        })

        const deliveries = routeOrders.filter(o =>
          o.destPort === portCode && pickedOrders.some(p => p.orderID === o.orderID)
        )

        const pickVol = ordersHere.reduce((s, o) => s + o.volumeTEU, 0)
        const delVol = deliveries.reduce((s, o) => s + o.volumeTEU, 0)
        const delRev = deliveries.reduce((s, o) => s + o.volumeTEU * o.revenuePerTEU, 0)

        currentLoad += pickVol - delVol
        deliveredRevenue += delRev
        for (const o of ordersHere) pickedOrders.push(o)

        if (portIdx > 0) {
          legHistory.push({
            fromPort: schedule[portIdx - 1].port,
            toPort: portCode,
            loadAtDeparture: currentLoad,
            pickedUp: pickVol,
            delivered: delVol,
            revenueEarned: delRev,
          })
        }
      }

      result.push({
        shipID, shipName, routeID: routeInfo.routeID, weekOffset: weekIdx,
        currentLoadTEU: Math.max(0, currentLoad),
        maxCapacityTEU: routeInfo.shipCapacity,
        pickedOrders, deliveredRevenue,
        currentPort, legHistory,
      })
    }
  }

  return result
}

export function computeSimulationMetrics(
  orders: Order[],
  shipStates: ShipLoadState[],
  simTimeHours: number,
): SimulationMetrics {
  const totalRevenue = shipStates.reduce((s, sh) => s + sh.deliveredRevenue, 0)
  const totalCapacity = shipStates.reduce((s, sh) => s + sh.maxCapacityTEU, 0)
  const totalLoad = shipStates.reduce((s, sh) => s + sh.currentLoadTEU, 0)
  const averageUtilization = totalCapacity > 0 ? (totalLoad / totalCapacity) * 100 : 0

  const routeOrders = orders.filter(o => o.routeID && o.deadline > 0)
  const deliveredCount = routeOrders.filter(o => {
    return shipStates.some(sh =>
      sh.pickedOrders.some(p => p.orderID === o.orderID) &&
      o.destPort === sh.currentPort
    )
  }).length
  const onTimeCount = routeOrders.filter(o => {
    const sh = shipStates.find(sh => sh.pickedOrders.some(p => p.orderID === o.orderID))
    if (!sh) return false
    const destIdx = sh.pickedOrders.find(p => p.orderID === o.orderID)
    return destIdx && sh.currentPort === o.destPort
  }).length

  const globalDelayRate = routeOrders.length > 0
    ? ((routeOrders.length - onTimeCount) / routeOrders.length) * 100
    : 0

  return {
    totalRevenue,
    averageUtilization,
    globalDelayRate,
    revenueTimeline: [{ time: simTimeHours, revenue: totalRevenue }],
  }
}

export function getOrdersForWeek(
  orders: Order[],
  routeID: string,
  week: number,
): Order[] {
  const offsetHours = week * 168
  const nextOffsetHours = (week + 1) * 168
  return orders.filter(o =>
    o.routeID === routeID &&
    o.deadline >= offsetHours &&
    o.deadline < nextOffsetHours
  )
}

export function exportOrdersJSON(orders: Order[]): string {
  return JSON.stringify(orders, null, 2)
}

export function getOrdersForWeekAllRoutes(orders: Order[], week: number): Order[] {
  const offsetHours = week * 168
  const nextOffsetHours = (week + 1) * 168
  return orders.filter(o =>
    o.deadline >= offsetHours &&
    o.deadline < nextOffsetHours
  )
}

export async function runGurobiOptimization(
  orders: Order[],
  week: number,
): Promise<Order[]> {
  const weekOrders = getOrdersForWeekAllRoutes(orders, week)
  if (weekOrders.length === 0) {
    throw new Error(`第${week}周暂无订单，无法启动优化`)
  }

  const payload = {
    orders: weekOrders.map(o => ({
      orderID: o.orderID,
      originPort: o.originPort,
      destPort: o.destPort,
      revenuePerTEU: o.revenuePerTEU,
      volumeTEU: o.volumeTEU,
      routeID: o.routeID,
      deadline: o.deadline,
    })),
    week,
  }

  const res = await fetch('/api/gurobi/solve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `优化失败 (${res.status})`)
  }

  const data = await res.json()
  const planned: Order[] = (data.planned_orders || []).map((o: any) => ({
    orderID: o.orderID,
    originPort: o.originPort,
    destPort: o.destPort,
    revenuePerTEU: Number(o.revenuePerTEU),
    volumeTEU: Number(o.volumeTEU),
    routeID: o.routeID,
    deadline: Number(o.deadline),
  }))

  const otherOrders = orders.filter(o => {
    const ow = Math.floor(o.deadline / 168)
    return ow !== week
  })

  return [...otherOrders, ...planned]
}