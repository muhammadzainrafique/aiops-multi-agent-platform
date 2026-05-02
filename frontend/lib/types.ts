export interface Incident {
  id:                 string
  alert_name:         string
  namespace:          string
  pod_name:           string
  severity:           'critical' | 'warning' | 'info'
  status:             'open' | 'in_progress' | 'evaluated' | 'resolved' | 'evaluation_failed' | 'resolution_failed'
  raw_logs:           string
  ai_diagnosis:       string
  recommended_action: string
  action_taken:       string
  created_at:         string
  resolved_at:        string | null
}

export interface HealthData {
  agent:     string
  status:    'healthy' | 'degraded' | 'offline'
  redis:     string
  timestamp: string
}

export interface ChartPoint {
  time:     string
  total:    number
  resolved: number
  open:     number
  failed:   number
}
