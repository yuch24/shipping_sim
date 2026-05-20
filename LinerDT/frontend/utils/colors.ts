export const SHIP_COLORS: Record<string, string> = {
  IDLE: '#9CA3AF',
  SAILING: '#3B82F6',
  ARRIVING: '#F59E0B',
  BERTHING: '#10B981',
  WAITING: '#EF4444',
  LOADING: '#F97316',
  UNLOADING: '#F97316',
  DEPARTING: '#06B6D4',
  default: '#FFFFFF',
}

export const CII_RATING_COLORS: Record<string, string> = {
  A: '#22c55e',
  B: '#84cc16',
  C: '#eab308',
  D: '#f97316',
  E: '#ef4444',
}

export const PORT_STATUS_COLORS = {
  NORMAL: '#3B82F6',
  BUSY: '#f59e0B',
  CONGESTED: '#ef4444',
}

export const ROUTE_COLORS = {
  AEU_ROUTE: '#06b6d4',
  SAILING_TRACE: '#3b82f6',
  DELAY_TRACE: '#f97316',
}

export const CARBON_INTENSITY_COLORS = {
  LOW: '#22c55e',
  MEDIUM: '#eab308',
  HIGH: '#f97316',
  EXTREME: '#ef4444',
}

export const ECA_ZONE_COLOR = '#a855f7'

export function getShipColor(state: string): string {
  return SHIP_COLORS[state] || SHIP_COLORS.default
}

export function getCIIRatingColor(rating: string): string {
  return CII_RATING_COLORS[rating] || CII_RATING_COLORS.B
}

export function getCarbonIntensityColor(carbonPerKm: number): string {
  if (carbonPerKm < 10) return CARBON_INTENSITY_COLORS.LOW
  if (carbonPerKm < 20) return CARBON_INTENSITY_COLORS.MEDIUM
  if (carbonPerKm < 40) return CARBON_INTENSITY_COLORS.HIGH
  return CARBON_INTENSITY_COLORS.EXTREME
}

export function getPortStatusColor(queueLength: number, totalBerths: number): string {
  const occupancyRatio = queueLength / (totalBerths * 2)
  if (occupancyRatio < 0.3) return PORT_STATUS_COLORS.NORMAL
  if (occupancyRatio < 0.7) return PORT_STATUS_COLORS.BUSY
  return PORT_STATUS_COLORS.CONGESTED
}
