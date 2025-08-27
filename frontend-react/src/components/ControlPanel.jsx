import { useState } from 'react'
import '../styles/ControlPanel.css'

function ControlPanel({ onRefresh, metrics }) {
  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = async () => {
    setIsRefreshing(true)
    onRefresh()
    setTimeout(() => {
      setIsRefreshing(false)
    }, 2000)
  }

  return (
    <div className="control-panel">
      <h2 className="panel-title">🎛️ Control Center</h2>
      
      <div className="control-section">
        <h3>System Controls</h3>
        <button 
          className={`refresh-btn ${isRefreshing ? 'refreshing' : ''}`}
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          {isRefreshing ? '🔄 Refreshing...' : '🔄 Refresh Topology'}
        </button>
      </div>

      <div className="control-section">
        <h3>Cluster Metrics</h3>
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-icon">🖥️</div>
            <div className="metric-value">{metrics.totalGpus}</div>
            <div className="metric-label">Total GPUs</div>
          </div>
          
          <div className="metric-card">
            <div className="metric-icon">🔗</div>
            <div className="metric-value">{metrics.activeConnections}</div>
            <div className="metric-label">Active Links</div>
          </div>
          
          <div className="metric-card">
            <div className="metric-icon">🌡️</div>
            <div className="metric-value">{metrics.avgTemperature}°C</div>
            <div className="metric-label">Avg Temp</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ControlPanel