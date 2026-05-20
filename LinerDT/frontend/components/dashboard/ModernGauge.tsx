'use client'

import ReactECharts from 'echarts-for-react'

interface ModernGaugeProps {
  value: number
  max?: number
  label: string
  unit?: string
  thresholds?: {
    warning?: number
    danger?: number
  }
  size?: number
  className?: string
}

export default function ModernGauge({
  value,
  max = 100,
  label,
  unit = '%',
  thresholds = {},
  size = 200,
  className = '',
}: ModernGaugeProps) {
  const getColor = () => {
    const percentage = (value / max) * 100
    if (thresholds.danger && percentage >= thresholds.danger) return '#ef4444'
    if (thresholds.warning && percentage >= thresholds.warning) return '#eab308'
    return '#22c55e'
  }

  const option = {
    series: [
      {
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: max,
        radius: '90%',
        pointer: {
          show: true,
          length: '60%',
          width: 6,
          itemStyle: {
            color: getColor(),
          },
        },
        progress: {
          show: true,
          width: 12,
          roundCap: true,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: '#1e3a5f' },
                { offset: 1, color: getColor() },
              ],
            },
          },
        },
        axisLine: {
          lineStyle: {
            width: 12,
            color: [[1, '#1e293b']],
          },
        },
        axisTick: {
          show: false,
        },
        splitLine: {
          show: false,
        },
        axisLabel: {
          show: false,
        },
        anchor: {
          show: false,
        },
        title: {
          show: true,
          offsetCenter: [0, '40%'],
          fontSize: 12,
          color: '#9ca3af',
        },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, '10%'],
          fontSize: size * 0.15,
          fontWeight: 'bold',
          formatter: `{value}${unit}`,
          color: getColor(),
        },
        data: [{ value: Math.round(value * 10) / 10, name: label }],
      },
    ],
  }

  return (
    <div className={className} style={{ width: size, height: size * 0.8 }}>
      <ReactECharts option={option} style={{ width: '100%', height: '100%' }} />
    </div>
  )
}