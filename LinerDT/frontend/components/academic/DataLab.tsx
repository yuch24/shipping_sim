'use client'

import { useState, useCallback, useEffect, useRef } from 'react'

interface DataLabProps {
  onOpenResult?: (title: string, content: React.ReactNode) => void
}

export default function DataLab({ onOpenResult }: DataLabProps) {
  const [dragOver, setDragOver] = useState(false)
  const [datasets, setDatasets] = useState<any[]>([])
  const [preview, setPreview] = useState<any>(null)
  const [importing, setImporting] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadDatasets = useCallback(() => {
    fetch('/api/academic-lab/datasets')
      .then(r => r.json())
      .then(data => setDatasets(data.datasets || []))
      .catch(() => setDatasets([]))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadDatasets() }, [loadDatasets])

  const handlePreview = async (id: string) => {
    try {
      const res = await fetch(`/api/academic-lab/datasets/${id}`)
      if (res.ok) {
        const data = await res.json()
        setPreview(data)
      }
    } catch { /* ignore */ }
  }

  const handleImport = async (id: string) => {
    setImporting(id)
    try {
      const res = await fetch(`/api/academic-lab/datasets/${id}/import`, { method: 'POST' })
      const data = await res.json()
      if (onOpenResult) {
        onOpenResult(`导入结果: ${id}`, (
          <div className="space-y-2">
            <div className={`px-3 py-2 rounded ${data.success ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'} text-xs`}>
              {data.message || (data.success ? '导入成功' : '导入失败')}
            </div>
            {data.count && <div className="text-gray-400 text-xs">共 {data.count} 条记录</div>}
          </div>
        ))
      }
    } catch { /* ignore */ }
    setImporting(null)
  }

  const doUpload = useCallback(async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!['csv', 'json', 'xlsx', 'xls'].includes(ext || '')) {
      if (onOpenResult) {
        onOpenResult('上传失败', (
          <div className="text-red-400 text-xs">不支持的文件格式: .{ext}，请上传 CSV 或 JSON 文件</div>
        ))
      }
      return
    }
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch('/api/academic-lab/datasets/upload', { method: 'POST', body: formData })
      const data = await res.json()
      if (data.success) {
        if (onOpenResult) {
          onOpenResult(`上传成功: ${file.name}`, (
            <div className="space-y-2">
              <div className="text-green-400 text-xs">{data.message}</div>
              <div className="bg-white/5 rounded overflow-auto max-h-48">
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="border-b border-white/10 bg-white/5">
                      {data.dataset.columns?.map((h: string) => (
                        <th key={h} className="text-left px-2 py-1 text-gray-500 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.dataset.rows?.slice(0, 10).map((row: any[], i: number) => (
                      <tr key={i} className="border-b border-white/5">
                        {row.map((v: any, j: number) => (
                          <td key={j} className="px-2 py-0.5 text-gray-400">{String(v ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))
        }
        loadDatasets()
      } else {
        if (onOpenResult) {
          onOpenResult('上传失败', (
            <div className="text-red-400 text-xs">{data.message || '服务器处理失败'}</div>
          ))
        }
      }
    } catch (e) {
      if (onOpenResult) {
        onOpenResult('上传失败', (
          <div className="text-red-400 text-xs">网络错误: {String(e)}</div>
        ))
      }
    }
    setUploading(false)
  }, [onOpenResult, loadDatasets])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) doUpload(file)
    if (e.target) e.target.value = ''
  }, [doUpload])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) doUpload(file)
  }, [doUpload])

  const handleClickUpload = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  return (
    <div className="h-full overflow-auto p-4">
      <div className="max-w-4xl mx-auto space-y-4">

        {/* 上传区 */}
        <div
          onClick={handleClickUpload}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`
            border-2 border-dashed rounded-lg p-8 text-center transition-all cursor-pointer
            ${dragOver
              ? 'border-marine-400 bg-marine-500/10'
              : uploading
                ? 'border-marine-500/50 bg-marine-500/5'
                : 'border-white/10 hover:border-white/20 bg-white/5'
            }
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.json,.xlsx,.xls"
            className="hidden"
            onChange={handleFileSelect}
          />
          {uploading ? (
            <div className="flex items-center justify-center gap-2">
              <svg className="w-5 h-5 animate-spin text-marine-400" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <p className="text-sm text-marine-400">上传解析中...</p>
            </div>
          ) : (
            <>
              <svg className="w-8 h-8 mx-auto mb-2 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="text-sm text-gray-400 mb-1">拖拽数据集文件到此处，或点击上传</p>
              <p className="text-[10px] text-gray-600">支持 CSV · JSON · Excel 格式</p>
            </>
          )}
        </div>

        {/* 预置数据集 */}
        <div>
          <h3 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            预置数据集 {!loading && <span className="text-gray-600 font-normal">({datasets.length})</span>}
          </h3>
          {loading ? (
            <div className="text-xs text-gray-600 py-4 text-center">加载中...</div>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              {datasets.map((ds: any) => (
                <div
                  key={ds.id}
                  className="bg-white/5 rounded-lg p-3 border border-white/10 hover:border-white/20 transition-colors cursor-pointer group"
                  onClick={() => handlePreview(ds.id)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="text-xs font-medium text-gray-300 group-hover:text-white transition-colors">{ds.name}</p>
                      <p className="text-[10px] text-gray-500 mt-0.5">{ds.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-gray-600">{ds.rows} 行 · {ds.fields?.length || 0} 字段</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleImport(ds.id) }}
                      disabled={importing === ds.id}
                      className="text-[10px] text-marine-400 opacity-0 group-hover:opacity-100 transition-opacity hover:text-marine-300 disabled:opacity-50"
                    >
                      {importing === ds.id ? '导入中...' : '导入仿真'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 数据预览 */}
        {preview && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-medium text-gray-400">数据预览 — {preview.name}</h3>
              <button onClick={() => setPreview(null)} className="text-[10px] text-gray-500 hover:text-white">关闭</button>
            </div>
            <div className="bg-white/5 rounded-lg border border-white/10 overflow-hidden">
              <div className="overflow-x-auto max-h-48">
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="border-b border-white/10 bg-white/5 sticky top-0">
                      {preview.columns?.map((h: string) => (
                        <th key={h} className="text-left px-3 py-1.5 text-gray-500 font-medium whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows?.slice(0, 20).map((row: any[], i: number) => (
                      <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                        {row.map((v: any, j: number) => (
                          <td key={j} className="px-3 py-1 text-gray-400 whitespace-nowrap">{String(v ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-3 py-1 text-[10px] text-gray-600 border-t border-white/5">
                显示 {Math.min(preview.rows?.length || 0, 20)} / {preview.rows?.length || 0} 行
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
