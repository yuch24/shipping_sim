'use client'

import ReactECharts from 'echarts-for-react'

interface RadialBarChartProps {
  data: { name: string; value: number; color: string }[]
  size?: number
  className?: string
}

export default function RadialBarChart({
  data,
  size = 200,
  className = '',
}: RadialBarChartProps) {
  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(10, 25, 47, 0.9)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: {
        color: '#fff',
      },
    },
    series: [
      {
        type: 'bar',
        data: data.map((d) => ({
          value: d.value,
          name: d.name,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: d.color + '40' },
                { offset: 1, color: d.color },
              ],
            },
            borderRadius: [0, 4, 4, 0],
          },
        })),
        backgroundStyle: {
          color: '#1e293b',
          borderRadius: [0, 4, 4, 0],
        },
        barWidth: '50%',
        showBackground: true,
        coordinateSystem: 'polar',
        roundCap: true,
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}',
          color: '#9ca3af',
          fontSize: 10,
        },
        max: Math.max(...data.map((d) => d.value)) * 1.2,
      },
    ],
    polar: {
      radius: ['60%', '90%'],
    },
    angleAxis: {
      max: Math.max(...data.map((d) => d.value)) * 1.2,
      show: false,
    },
    radiusAxis: {
      type: 'category',
      data: data.map((d) => d.name),
      show: false,
    },
  }

  return (
    <div className={className} style={{ width: size, height: size }}>
      <ReactECharts option={option} style={{ width: '100%', height: '100%' }} />
    </div>
  )
}