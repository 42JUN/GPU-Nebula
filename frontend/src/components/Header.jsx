import { useState, useEffect } from 'react'
import '../styles/Header.css'

function Header() {
  const [currentTime, setCurrentTime] = useState(new Date())
  const [systemStatus, setSystemStatus] = useState('online')
  const [uptimeSeconds, setUptimeSeconds] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
      setUptimeSeconds(prev => prev + 1)
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { 
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const formatUptime = (seconds) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    return `${hours}h ${minutes}m ${secs}s`
  }

  return (
    <header className="header">
      <div className="header-left">
        <h1 className="header-title">⚡ GPU Nebula</h1>
        <p className="header-subtitle">Advanced GPU Cluster Management</p>
      </div>
      
      <div className="header-right">
        <div className="time-display">
          🕒 {formatTime(currentTime)}
        </div>
        <div className="status-indicator online">
          <span className="status-dot"></span>
          <span>System Online</span>
        </div>
      </div>
    </header>
  )
}

export default Header