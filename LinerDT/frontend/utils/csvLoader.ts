// CSV data loader — reads port_coordinates.csv and route_waypoints.csv

import portCsvRaw from '../data/port_coordinates.csv'
import waypointCsvRaw from '../data/route_waypoints.csv'

export interface WaypointDataCSV {
  segment_id: string
  from_port: string
  to_port: string
  seq: number
  lat: number
  lon: number
  description: string
}

function parseCsv(raw: string): string[][] {
  const lines = raw.trim().split('\n')
  const header = lines[0].split(',')
  return lines.slice(1).map(line => {
    const fields: string[] = []
    let current = ''
    let inQuote = false
    for (const ch of line) {
      if (ch === '"') { inQuote = !inQuote }
      else if (ch === ',' && !inQuote) { fields.push(current); current = '' }
      else { current += ch }
    }
    fields.push(current)
    return fields
  })
}

export function loadPortsFromCsv(): Record<string, [number, number]> {
  const rows = parseCsv(portCsvRaw)
  const result: Record<string, [number, number]> = {}
  for (const row of rows) {
    const port_code = row[0]?.trim()
    const lat = parseFloat(row[3])
    const lon = parseFloat(row[4])
    if (port_code && !isNaN(lat) && !isNaN(lon)) {
      result[port_code] = [lat, lon]
    }
  }
  return result
}

export interface PortDataCSV {
  port_code: string
  port_name: string
  terminal_name: string
  lat: number
  lon: number
  region: string
}

export function loadPortsFullFromCsv(): PortDataCSV[] {
  const rows = parseCsv(portCsvRaw)
  return rows.map(row => ({
    port_code: row[0]?.trim(),
    port_name: row[1]?.trim(),
    terminal_name: row[2]?.trim(),
    lat: parseFloat(row[3]),
    lon: parseFloat(row[4]),
    region: row[5]?.trim(),
  }))
}

export function loadWaypointsFromCsv(): Record<string, { from_port: string; to_port: string; points: [number, number][] }> {
  const rows = parseCsv(waypointCsvRaw)
  const groups: Record<string, { from_port: string; to_port: string; points: [number, number][] }> = {}
  for (const row of rows) {
    const segId = row[0]?.trim()
    const fromPort = row[1]?.trim()
    const toPort = row[2]?.trim()
    const seq = parseInt(row[3])
    const lat = parseFloat(row[4])
    const lon = parseFloat(row[5])
    if (!segId || isNaN(lat) || isNaN(lon)) continue
    if (!groups[segId]) {
      groups[segId] = { from_port: fromPort, to_port: toPort, points: [] }
    }
    groups[segId].points.push([lat, lon])
  }
  for (const g of Object.values(groups)) {
    g.points.sort((a, b) => {
      return 0
    })
  }
  return groups
}

export function buildSegmentMapFromCsv(): Map<string, { from: string; to: string; waypoints: [number, number][] }> {
  const groups = loadWaypointsFromCsv()
  const map = new Map<string, { from: string; to: string; waypoints: [number, number][] }>()
  for (const [segId, group] of Object.entries(groups)) {
    map.set(segId, { from: group.from_port, to: group.to_port, waypoints: group.points })
  }
  return map
}