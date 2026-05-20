'use client'

import { useState, useCallback } from 'react'
import { Order, ROUTE_PORT_INFO } from '@/types/order'
import { getOrdersForWeek, exportOrdersJSON, runGurobiOptimization } from '@/utils/shipLoading'

interface OrderManagerProps {
  orders: Order[]
  onOrdersChange: (orders: Order[]) => void
}

export default function OrderManager({ orders, onOrdersChange }: OrderManagerProps) {
  const [selectedRoute, setSelectedRoute] = useState('AEU1')
  const [selectedWeek, setSelectedWeek] = useState(1)
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingOrder, setEditingOrder] = useState<Order | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [gurobiLoading, setGurobiLoading] = useState(false)
  const [gurobiError, setGurobiError] = useState<string | null>(null)

  const routeInfo = ROUTE_PORT_INFO.find(r => r.routeID === selectedRoute)!
  const weekOrders = getOrdersForWeek(orders, selectedRoute, selectedWeek)

  const filteredOrders = searchTerm
    ? weekOrders.filter(o =>
        o.orderID.toLowerCase().includes(searchTerm.toLowerCase()) ||
        o.originPort.toLowerCase().includes(searchTerm.toLowerCase()) ||
        o.destPort.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : weekOrders

  const getNextOrderID = () => {
    const prefix = selectedRoute
    const existing = orders.filter(o => o.orderID.startsWith(prefix))
    const num = existing.length + 1
    return `${prefix}_ORD_${String(num).padStart(3, '0')}`
  }

  const handleAddOrder = (newOrder: Order) => {
    onOrdersChange([...orders, newOrder])
    setShowAddForm(false)
  }

  const handleUpdateOrder = (updated: Order) => {
    onOrdersChange(orders.map(o => o.orderID === updated.orderID ? updated : o))
    setEditingOrder(null)
  }

  const handleDeleteOrder = (orderID: string) => {
    onOrdersChange(orders.filter(o => o.orderID !== orderID))
  }

  const handleExport = () => {
    const json = exportOrdersJSON(orders)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `orders_${selectedRoute}_week${selectedWeek}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleGurobiOptimize = useCallback(async () => {
    setGurobiLoading(true)
    setGurobiError(null)
    try {
      const newOrders = await runGurobiOptimization(orders, selectedWeek)
      onOrdersChange(newOrders)
    } catch (e: any) {
      setGurobiError(e.message || '优化失败')
    } finally {
      setGurobiLoading(false)
    }
  }, [orders, selectedWeek, onOrdersChange])

  const getWeekDeadlineRange = (week: number) => {
    const start = week * 168
    const end = (week + 1) * 168
    return { start, end }
  }

  return (
    <div className="flex flex-col h-full bg-[#0a1929] text-white overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 shrink-0">
        <h2 className="text-sm font-semibold text-marine-400">订单管理</h2>
        <div className="flex gap-1">
          <button onClick={handleExport} className="px-2 py-1 text-[10px] bg-marine-500/20 text-marine-400 hover:bg-marine-500/30 rounded transition-colors">
            导出JSON
          </button>
          <button
            onClick={handleGurobiOptimize}
            disabled={gurobiLoading}
            className={`px-2 py-1 text-[10px] rounded transition-colors font-medium ${
              gurobiLoading
                ? 'bg-yellow-500/20 text-yellow-400 cursor-wait'
                : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
            }`}
          >
            {gurobiLoading ? '计算中...' : '启动Gurobi优化'}
          </button>
        </div>
      </div>

      {/* Gurobi error */}
      {gurobiError && (
        <div className="px-3 py-1.5 text-[10px] bg-red-500/10 border-b border-red-500/20 text-red-400">
          {gurobiError}
          <button onClick={() => setGurobiError(null)} className="ml-2 text-red-500 hover:text-red-300">关闭</button>
        </div>
      )}

      {/* Route + Week tabs */}
      <div className="px-3 py-2 shrink-0 space-y-1.5">
        <div className="flex gap-1">
          {ROUTE_PORT_INFO.map(r => (
            <button
              key={r.routeID}
              onClick={() => { setSelectedRoute(r.routeID); setSelectedWeek(1) }}
              className={`px-2 py-1 text-[10px] font-medium rounded transition-all ${
                selectedRoute === r.routeID
                  ? 'bg-marine-500 text-white'
                  : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-gray-300'
              }`}
            >
              {r.routeID} ({r.cycleWeeks}周)
            </button>
          ))}
        </div>

        <div className="flex gap-0.5 overflow-x-auto pb-1">
          {Array.from({ length: routeInfo.cycleWeeks }, (_, i) => i + 1).map(w => (
            <button
              key={w}
              onClick={() => setSelectedWeek(w)}
              className={`px-1.5 py-0.5 text-[9px] font-mono rounded shrink-0 transition-all ${
                selectedWeek === w
                  ? 'bg-marine-500/30 text-marine-400 border border-marine-400/50'
                  : 'bg-white/5 text-gray-500 hover:bg-white/10 hover:text-gray-300 border border-transparent'
              }`}
            >
              W{w}
            </button>
          ))}
        </div>

        {/* Search */}
        <input
          type="text"
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          placeholder="搜索订单..."
          className="w-full px-2 py-1 text-[10px] bg-white/5 border border-white/10 rounded text-gray-300 placeholder-gray-600 focus:outline-none focus:border-marine-400/50"
        />
      </div>

      {/* Order table */}
      <div className="flex-1 overflow-y-auto px-3">
        <table className="w-full text-[10px]">
          <thead className="sticky top-0 bg-[#0a1929]">
            <tr className="text-gray-500 border-b border-white/5">
              <th className="py-1 text-left font-medium">ID</th>
              <th className="py-1 text-left font-medium">起→终</th>
              <th className="py-1 text-right font-medium">TEU</th>
              <th className="py-1 text-right font-medium">$TEU</th>
              <th className="py-1 text-right font-medium">截止</th>
              <th className="py-1 text-center font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredOrders.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-6 text-center text-gray-600 text-[10px]">
                  第{selectedWeek}周暂无订单
                </td>
              </tr>
            ) : (
              filteredOrders.map(o => {
                const origName = routeInfo.portNames[o.originPort] || o.originPort
                const destName = routeInfo.portNames[o.destPort] || o.destPort
                const deadlineDays = Math.floor(o.deadline / 24)
                return (
                  <tr key={o.orderID} className="border-b border-white/5 hover:bg-white/[0.02]">
                    <td className="py-1.5 text-marine-400 font-mono">{o.orderID}</td>
                    <td className="py-1.5">
                      <span className="text-emerald-400">{origName}</span>
                      <span className="text-gray-600 mx-0.5">→</span>
                      <span className="text-amber-400">{destName}</span>
                    </td>
                    <td className="py-1.5 text-right font-mono text-gray-300">{o.volumeTEU}</td>
                    <td className="py-1.5 text-right font-mono text-emerald-400">${o.revenuePerTEU}</td>
                    <td className="py-1.5 text-right font-mono text-gray-400">D{deadlineDays + 1}</td>
                    <td className="py-1.5 text-center">
                      <button onClick={() => setEditingOrder(o)} className="px-1 text-gray-500 hover:text-blue-400 transition-colors">编辑</button>
                      <button onClick={() => handleDeleteOrder(o.orderID)} className="px-1 text-gray-500 hover:text-red-400 transition-colors">删除</button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Add button */}
      <div className="px-3 py-2 border-t border-white/10 shrink-0">
        <button
          onClick={() => setShowAddForm(true)}
          className="w-full px-3 py-1.5 text-[11px] bg-marine-500/20 text-marine-400 hover:bg-marine-500/30 rounded transition-colors font-medium"
        >
          + 新增订单 (第{selectedWeek}周 / {selectedRoute})
        </button>
      </div>

      {/* Add/Edit form overlay */}
      {(showAddForm || editingOrder) && (
        <OrderForm
          routeInfo={routeInfo}
          week={selectedWeek}
          existingOrder={editingOrder}
          nextOrderID={editingOrder ? editingOrder.orderID : getNextOrderID()}
          onSave={editingOrder ? handleUpdateOrder : handleAddOrder}
          onCancel={() => { setShowAddForm(false); setEditingOrder(null) }}
        />
      )}
    </div>
  )
}

interface OrderFormProps {
  routeInfo: typeof ROUTE_PORT_INFO[number]
  week: number
  existingOrder: Order | null
  nextOrderID: string
  onSave: (order: Order) => void
  onCancel: () => void
}

function OrderForm({ routeInfo, week, existingOrder, nextOrderID, onSave, onCancel }: OrderFormProps) {
  const [originPort, setOriginPort] = useState(existingOrder?.originPort || '')
  const [destPort, setDestPort] = useState(existingOrder?.destPort || '')
  const [volumeTEU, setVolumeTEU] = useState(existingOrder?.volumeTEU || 500)
  const [revenuePerTEU, setRevenuePerTEU] = useState(existingOrder?.revenuePerTEU || 200)
  const [deadline, setDeadline] = useState(existingOrder?.deadline || week * 168)
  const [errors, setErrors] = useState<string[]>([])

  const validate = () => {
    const errs: string[] = []
    if (!originPort) errs.push('请选择起运港')
    if (!destPort) errs.push('请选择目的港')
    if (originPort === destPort) errs.push('起运港与目的港不能相同')
    if (!routeInfo.ports.includes(originPort)) errs.push(`起运港不在${routeInfo.routeID}航线上`)
    if (!routeInfo.ports.includes(destPort)) errs.push(`目的港不在${routeInfo.routeID}航线上`)
    if (volumeTEU <= 0) errs.push('TEU量必须大于0')
    if (revenuePerTEU <= 0) errs.push('每TEU收益必须大于0')
    setErrors(errs)
    return errs.length === 0
  }

  const handleSubmit = () => {
    if (!validate()) return
    onSave({
      orderID: nextOrderID,
      originPort,
      destPort,
      volumeTEU,
      revenuePerTEU,
      routeID: routeInfo.routeID,
      deadline,
    })
  }

  return (
    <div className="absolute inset-0 bg-[#0a1929]/95 z-30 flex flex-col">
      <div className="px-4 py-2 border-b border-white/10 shrink-0">
        <h3 className="text-xs font-medium text-white">
          {existingOrder ? '编辑订单' : '新增订单'} — {routeInfo.routeID} 第{week}周
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {errors.length > 0 && (
          <div className="p-2 bg-red-500/10 border border-red-500/30 rounded text-[10px] text-red-400">
            {errors.map(e => <div key={e}>{e}</div>)}
          </div>
        )}

        <div>
          <label className="text-[10px] text-gray-500 mb-1 block">起运港</label>
          <select value={originPort} onChange={e => setOriginPort(e.target.value)}
            className="w-full px-2 py-1.5 text-[10px] bg-white/5 border border-white/10 rounded text-gray-300 focus:outline-none focus:border-marine-400/50">
            <option value="">-- 选择起运港 --</option>
            {routeInfo.ports.map(p => (
              <option key={p} value={p}>{routeInfo.portNames[p]} ({p})</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-[10px] text-gray-500 mb-1 block">目的港</label>
          <select value={destPort} onChange={e => setDestPort(e.target.value)}
            className="w-full px-2 py-1.5 text-[10px] bg-white/5 border border-white/10 rounded text-gray-300 focus:outline-none focus:border-marine-400/50">
            <option value="">-- 选择目的港 --</option>
            {routeInfo.ports.map(p => (
              <option key={p} value={p}>{routeInfo.portNames[p]} ({p})</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] text-gray-500 mb-1 block">TEU量</label>
            <input type="number" value={volumeTEU} onChange={e => setVolumeTEU(Number(e.target.value))}
              className="w-full px-2 py-1.5 text-[10px] bg-white/5 border border-white/10 rounded text-gray-300 focus:outline-none focus:border-marine-400/50" min={1} />
          </div>
          <div>
            <label className="text-[10px] text-gray-500 mb-1 block">收益/TEU ($)</label>
            <input type="number" value={revenuePerTEU} onChange={e => setRevenuePerTEU(Number(e.target.value))}
              className="w-full px-2 py-1.5 text-[10px] bg-white/5 border border-white/10 rounded text-gray-300 focus:outline-none focus:border-marine-400/50" min={1} />
          </div>
        </div>

        <div>
          <label className="text-[10px] text-gray-500 mb-1 block">截止时间 (小时)</label>
          <input type="number" value={deadline} onChange={e => setDeadline(Number(e.target.value))}
            className="w-full px-2 py-1.5 text-[10px] bg-white/5 border border-white/10 rounded text-gray-300 focus:outline-none focus:border-marine-400/50" />
          <div className="text-[9px] text-gray-600 mt-0.5">第{week}周 ≈ {week * 168}h ~ {(week + 1) * 168}h</div>
        </div>
      </div>

      <div className="flex gap-2 px-4 py-2 border-t border-white/10 shrink-0">
        <button onClick={handleSubmit}
          className="flex-1 px-3 py-1.5 text-[11px] bg-marine-500 text-white hover:bg-marine-400 rounded transition-colors font-medium">
          {existingOrder ? '更新' : '添加'}
        </button>
        <button onClick={onCancel}
          className="flex-1 px-3 py-1.5 text-[11px] bg-white/10 text-gray-400 hover:bg-white/15 rounded transition-colors">
          取消
        </button>
      </div>
    </div>
  )
}