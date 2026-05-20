// Shared map data — port coordinates, route waypoints, route segments

// Port coordinates [lat, lon] — full 26 ports using Cesium-style IDs
export const PORT_COORDS: Record<string, [number, number]> = {
  // China
  'CNTAO': [36.0317, 120.2047],
  'CNSHA': [30.6306, 122.0733],
  'CNNGB': [29.9336, 121.9669],
  'CNXMN': [24.4914, 118.0747],
  'CNYTN': [22.5727, 114.2751],
  'CNTXG': [38.9756, 117.7339],
  'CNDLC': [38.9694, 121.6608],
  // Southeast Asia
  'SGSIN': [1.2672, 103.8342],
  'MYPKG': [2.9964, 101.3783],
  // Northern Europe
  'GBFXT': [51.9506, 1.3264],
  'BEZEE': [51.3414, 3.1808],
  'PLGDY': [54.3875, 18.6853],
  'DEWVN': [53.5892, 8.1433],
  'DEHAM': [53.5242, 9.9792],
  'NLRTM': [51.9525, 4.0258],
  'BEANR': [51.2731, 4.3558],
  'FRLEH': [49.4794, 0.1825],
  'FRDKK': [51.0397, 2.3717],
  'GBSOU': [50.8761, -1.3972],
  // Mediterranean / North Africa
  'MAPTM': [35.8439, -5.5122],
}

// Sea waypoints — format: [lat, lon]
export const SEA_WAYPOINTS: Record<string, number[][]> = {
  // China coastal (using port_code waypoints)
  COAST_CNTXG_CNDLC: [[38.9756, 117.7339], [39, 119], [39.2, 120.5], [38.9694, 121.6608]],
  COAST_CNDLC_CNTAO: [[38.9694, 121.6608], [37, 122], [36.8, 121.5], [36.0317, 120.2047]],
  COAST_CNTAO_CNSHA: [[36.0317, 120.2047], [35.5, 120.5], [34, 121.5], [32.5, 122], [30.6306, 122.0733]],
  COAST_CNSHA_CNNGB: [[30.6306, 122.0733], [30.8, 121.8], [29.9336, 121.9669]],
  COAST_CNSHA_CNYTN: [[30.6306, 122.0733], [30, 122], [29, 121.8], [28.5, 121.5], [27.5, 121], [26.5, 120.5], [25.5, 119.5], [24.5, 118.5], [23.5, 117.5], [23, 116], [22.8, 115], [22.5727, 114.2751]],
  COAST_CNNGB_CNXMN: [[29.9336, 121.9669], [28.5, 121.5], [27, 120.5], [25.5, 119.5], [24.4914, 118.0747]],
  COAST_CNNGB_SGSIN: [[29.9336, 121.9669], [28.5, 121.5], [27.5, 121], [26.5, 120.5], [25.5, 119.5], [24.5, 118.5], [23.5, 117.5], [22.8, 116], [20, 114.5], [18, 114], [15, 113], [12, 111], [8, 109], [6, 107.5], [4, 107], [2.5, 105.8], [2, 105.5], [1.2672, 103.8342]],
  COAST_CNXMN_CNYTN: [[24.4914, 118.0747], [23.5, 117], [23, 116], [22.5727, 114.2751]],
  // South China Sea (using port_code)
  SCS_CNYTN_SGSIN: [[22.5727, 114.2751], [20, 114.5], [18, 114], [15, 113], [12, 112], [8, 109], [4, 107], [2, 105.5], [1.2672, 103.8342]],
  // Cape of Good Hope route (Singapore → Cape → Atlantic → Channel)
  CAPE: [
    [1.3, 103.8], [0, 104.5], [-5.5, 106], [-10, 100], [-15, 93],
    [-20, 85], [-25, 75], [-30, 65], [-33, 55], [-34, 45],
    [-34.5, 35], [-34.5, 28], [-34.5, 18.5],
    [-25, 10], [-15, 2], [-5, -5], [5, -10], [15, -15],
    [25, -15], [35, -10], [45, -5], [48, -3],
  ],
  // North Sea coastal
  NORTH_SEA_RTM_HAM: [[51.92, 4.48], [52.5, 6], [53, 7], [53.5, 8], [53.55, 9.99]],
}

export function buildRoutePath(
  segments: string[][],
  coords: Record<string, [number, number]>,
  waypoints: Record<string, number[][]>,
): [number, number][] {
  if (!segments || segments.length === 0) return []
  const result: [number, number][] = []

  for (const seg of segments) {
    for (const id of seg) {
      if (coords[id]) {
        result.push([coords[id][0], coords[id][1]])
      } else if (waypoints[id]) {
        for (const wp of waypoints[id]) {
          result.push([wp[0], wp[1]])
        }
      }
    }
  }
  return result
}