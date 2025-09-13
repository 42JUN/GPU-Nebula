import { useState } from 'react'
import '../styles/ControlPanel.css'

function ControlPanel({ onRefresh, metrics }) {
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [selfGpu, setSelfGpu] = useState(null)
  const [isDetecting, setIsDetecting] = useState(false)

  const handleRefresh = async () => {
    setIsRefreshing(true)
    onRefresh()
    setTimeout(() => {
      setIsRefreshing(false)
    }, 2000)
  }

  const detectSelfGpu = async () => {
    try {
      setIsDetecting(true)
      
      // First, force detection and save to database
      const detectRes = await fetch('http://localhost:8080/gpu/detect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      const detectData = await detectRes.json()
      
      if (detectData.status === 'success') {
        // Get the detected GPU info
        const res = await fetch('http://localhost:8080/gpu/self')
        const data = await res.json()
        setSelfGpu(data.gpu || null)
        
        // Show success message
        alert(`✅ Successfully detected and saved ${detectData.gpus.length} GPU(s)!\nMethod: ${detectData.detection_method}`)
      } else {
        alert(`❌ Detection failed: ${detectData.message}`)
        setSelfGpu(null)
      }
    } catch (e) {
      console.error('GPU detection error:', e)
      alert(`❌ Error detecting GPU: ${e.message}`)
      setSelfGpu(null)
    } finally {
      setIsDetecting(false)
    }
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
        <button 
          className="refresh-btn detect-btn"
          onClick={detectSelfGpu}
          disabled={isDetecting}
        >
          {isDetecting ? '🧠 Detecting...' : '🧠 Detect My GPU'}
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

      {selfGpu && (
        <div className="control-section">
          <h3>My GPU</h3>
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-icon">🎯</div>
              <div className="metric-value" title={selfGpu.model}>{selfGpu.model}</div>
              <div className="metric-label">Model</div>
            </div>
            <div className="metric-card">
              <div className="metric-icon">🌡️</div>
              <div className="metric-value">{selfGpu.temperature ?? '-'}°C</div>
              <div className="metric-label">Temp</div>
            </div>
            <div className="metric-card">
              <div className="metric-icon">⚙️</div>
              <div className="metric-value">{selfGpu.utilization ?? '-'}%</div>
              <div className="metric-label">Util</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ControlPanel