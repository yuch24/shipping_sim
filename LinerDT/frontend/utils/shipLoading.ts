import type { Order, ShipLoadState, LegRecord, SimulationMetrics, PortBufferItem, AllocationPlan } from '@/types/order'
import { ROUTE_PORT_INFO, CYCLE_PORT_SEQUENCE } from '@/types/order'

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

type PortBuffer = Record<string, PortBufferItem[]>

export function isCyclicFeasible(origin: string, dest: string, routeID: string): boolean {
  const seq = CYCLE_PORT_SEQUENCE[routeID]
  if (!seq || origin === dest) return false
  let originIdx = -1
  for (let i = 0; i < seq.length; i++) { if (seq[i] === origin) { originIdx = i; break } }
  if (originIdx === -1) return false
  const n = seq.length
  for (let i = originIdx + 1; i < originIdx + n; i++) { if (seq[i % n] === dest) return true }
  return false
}

function initBufferForCycleWeek(
  portBuffer: PortBuffer,
  orders: Order[],
  routeID: string,
  cycleWeek: number,
): void {
  const weekOrders = orders.filter(o => o.routeID === routeID && o.week === cycleWeek)
  for (const o of weekOrders) {
    const key = `${routeID}|${cycleWeek}|${o.originPort}`
    if (!portBuffer[key]) portBuffer[key] = []
    const existing = portBuffer[key].find(bi => bi.orderID === o.orderID)
    if (!existing) {
      portBuffer[key].push({
        orderID: o.orderID, originPort: o.originPort, destPort: o.destPort,
        revenuePerTEU: o.revenuePerTEU, volumeTEU: o.volumeTEU,
        routeID: o.routeID, week: o.week, deadline: o.deadline,
        remainingTEU: o.volumeTEU,
      })
    }
  }
}

export function computeShipLoadStates(
  orders: Order[],
  simTimeHours: number,
  portBuffer: PortBuffer,
  allocationPlans?: AllocationPlan[],
): { states: ShipLoadState[]; portBuffer: PortBuffer } {
  const states: ShipLoadState[] = []
  const plansMap = new Map<string, AllocationPlan[]>()
  if (allocationPlans) {
    for (const p of allocationPlans) {
      const k = `${p.targetRoute}|${p.targetAbsWeek}|${p.orderID}`
      if (!plansMap.has(k)) plansMap.set(k, [])
      plansMap.get(k)!.push(p)
    }
  }

  for (const routeInfo of ROUTE_PORT_INFO) {
    const schedule = ROUTE_SCHEDULES_HOURS[routeInfo.routeID]
    if (!schedule) continue

    const cycleHours = schedule[schedule.length - 1].eta
    const numShips = routeInfo.cycleWeeks

    const simWeek = Math.floor(simTimeHours / 168)
    const routeCycleWeek = (simWeek % routeInfo.cycleWeeks) + 1

    initBufferForCycleWeek(portBuffer, orders, routeInfo.routeID, routeCycleWeek)

    for (let weekIdx = 0; weekIdx < numShips; weekIdx++) {
      const offset = weekIdx * 168
      const shipID = `${routeInfo.routeID}_s${String(weekIdx + 1).padStart(3, '0')}`
      const shipName = `${routeInfo.routeID} Ship ${weekIdx + 1}`

      if (simTimeHours < offset) {
        states.push({
          shipID, shipName, routeID: routeInfo.routeID, weekOffset: weekIdx,
          currentLoadTEU: 0, maxCapacityTEU: routeInfo.shipCapacity,
          pickedOrders: [], orderPickupTimes: {}, delayedOrderIDs: [],
          deliveredRevenue: 0, currentPort: schedule[0].port, legHistory: [],
        })
        continue
      }

      const cyclePos = (simTimeHours - offset) % cycleHours
      const absTime = offset + cyclePos

      let currentPortIdx = 0
      for (let i = 0; i < schedule.length; i++) { if (absTime >= schedule[i].eta) currentPortIdx = i }

      const currentPort = schedule[currentPortIdx].port
      let currentLoad = 0
      let deliveredRevenue = 0
      const pickedOrders: Order[] = []
      const orderPickupTimes: Record<string, number> = {}
      const delayedOrderIDs: string[] = []
      const legHistory: LegRecord[] = []

      for (let portIdx = 0; portIdx <= currentPortIdx; portIdx++) {
        const portCode = schedule[portIdx].port
        const portAbsTime = offset + schedule[portIdx].eta

        const bufKey = `${routeInfo.routeID}|${routeCycleWeek}|${portCode}`
        const bufferItems = portBuffer[bufKey] || []

        const shipAbsWeek = computeShipAbsWeek(offset, cycleHours, simTimeHours)
        const useGurobi = allocationPlans && allocationPlans.length > 0

        let pickVol = 0
        for (const bi of bufferItems) {
          if (bi.remainingTEU <= 0) continue
          const remaining = routeInfo.shipCapacity - currentLoad
          if (remaining <= 0) break

          if (useGurobi) {
            const planKey = `${routeInfo.routeID}|${shipAbsWeek}|${bi.orderID}`
            if (!plansMap.has(planKey)) continue
          }

          const take = Math.min(bi.remainingTEU, remaining)
          bi.remainingTEU -= take
          currentLoad += take
          pickVol += take

          orderPickupTimes[bi.orderID] = portAbsTime
          pickedOrders.push({
            orderID: bi.orderID, originPort: bi.originPort, destPort: bi.destPort,
            revenuePerTEU: bi.revenuePerTEU, volumeTEU: take,
            routeID: bi.routeID, week: bi.week, deadline: bi.deadline,
          })
        }

        portBuffer[bufKey] = bufferItems.filter(bi => bi.remainingTEU > 0)

        const deliveries = pickedOrders.filter(o => o.destPort === portCode)
        let delVol = 0
        let delRev = 0
        for (const o of deliveries) {
          delVol += o.volumeTEU
          delRev += o.volumeTEU * o.revenuePerTEU
          currentLoad -= o.volumeTEU

          const absoluteDeadline = orderPickupTimes[o.orderID] + o.deadline
          if (portAbsTime > absoluteDeadline) delayedOrderIDs.push(o.orderID)
        }
        deliveredRevenue += delRev

        if (portIdx > 0) {
          legHistory.push({
            fromPort: schedule[portIdx - 1].port, toPort: portCode,
            loadAtDeparture: currentLoad + delVol,
            pickedUp: pickVol, delivered: delVol, revenueEarned: delRev,
          })
        }
      }

      states.push({
        shipID, shipName, routeID: routeInfo.routeID, weekOffset: weekIdx,
        currentLoadTEU: Math.max(0, currentLoad),
        maxCapacityTEU: routeInfo.shipCapacity,
        pickedOrders, orderPickupTimes, delayedOrderIDs,
        deliveredRevenue, currentPort, legHistory,
      })
    }
  }

  return { states, portBuffer }
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

  const allPickedOrderIDs = new Set<string>()
  for (const sh of shipStates) for (const o of sh.pickedOrders) allPickedOrderIDs.add(o.orderID)
  const totalDelayed = shipStates.reduce((s, sh) => s + sh.delayedOrderIDs.length, 0)
  const globalDelayRate = allPickedOrderIDs.size > 0 ? (totalDelayed / allPickedOrderIDs.size) * 100 : 0

  const routeRevenue: Record<string, { total: number; average: number }> = {}
  const routeRevenueTimeline: Record<string, { time: number; revenue: number }[]> = {}
  let totalAverageRevenue = 0
  for (const ri of ROUTE_PORT_INFO) {
    const routeShips = shipStates.filter(sh => sh.routeID === ri.routeID)
    const rev = routeShips.reduce((s, sh) => s + sh.deliveredRevenue, 0)
    const avg = ri.cycleWeeks > 0 ? rev / ri.cycleWeeks : 0
    routeRevenue[ri.routeID] = { total: rev, average: avg }
    routeRevenueTimeline[ri.routeID] = [{ time: simTimeHours, revenue: rev }]
    totalAverageRevenue += avg
  }

  return {
    totalRevenue, averageUtilization, globalDelayRate,
    revenueTimeline: [{ time: simTimeHours, revenue: totalRevenue }],
    routeRevenue, totalAverageRevenue, routeRevenueTimeline,
  }
}

export function getOrdersForWeek(orders: Order[], routeID: string, week: number): Order[] {
  return orders.filter(o => o.routeID === routeID && o.week === week)
}

export function exportOrdersJSON(orders: Order[]): string {
  return JSON.stringify(orders, null, 2)
}

export function getOrdersForWeekAllRoutes(orders: Order[], week: number): Order[] {
  return orders.filter(o => o.week === week)
}

export async function runGurobiOptimization(orders: Order[], week: number): Promise<Order[]> {
  const weekOrders = getOrdersForWeekAllRoutes(orders, week)
  if (weekOrders.length === 0) throw new Error(`第${week}周暂无订单，无法启动优化`)

  const payload = {
    orders: weekOrders.map(o => ({
      orderID: o.orderID, originPort: o.originPort, destPort: o.destPort,
      revenuePerTEU: o.revenuePerTEU, volumeTEU: o.volumeTEU,
      routeID: o.routeID, deadline: o.deadline, week: o.week,
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
    orderID: o.orderID, originPort: o.originPort, destPort: o.destPort,
    revenuePerTEU: Number(o.revenuePerTEU), volumeTEU: Number(o.volumeTEU),
    routeID: o.routeID, week: o.week ?? week, deadline: Number(o.deadline),
  }))
  return [...orders.filter(o => o.week !== week), ...planned]
}

export function computeShipAbsWeek(
  offset: number,
  cycleHours: number,
  simTimeHours: number,
): number {
  const cyclePos = (simTimeHours - offset) % cycleHours
  const absTime = offset + cyclePos
  return Math.floor(absTime / 168)
}

export async function runRollingOptimization(
  currentAbsWeek: number,
  weekOrders: Order[],
  committedSnapshot: { routeID: string; absWeek: number; allocatedVolume: number }[],
  horizonWeeks: number = 4,
): Promise<{ allocationPlans: AllocationPlan[]; rejectedOrders: any[] }> {
  const payload = {
    currentAbsWeek,
    newOrders: weekOrders.map(o => ({
      orderID: o.orderID,
      originPort: o.originPort,
      destPort: o.destPort,
      revenuePerTEU: o.revenuePerTEU,
      volumeTEU: o.volumeTEU,
      routeID: o.routeID,
      deadline: o.deadline,
      week: o.week,
    })),
    committedSnapshot,
    horizonWeeks,
  }

  const res = await fetch('/api/gurobi/solve-rolling', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `滚动优化失败 (${res.status})`)
  }

  const data = await res.json()
  return {
    allocationPlans: data.allocationPlans || [],
    rejectedOrders: data.rejectedOrders || [],
  }
}
