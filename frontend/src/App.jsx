import { useState, useEffect } from 'react'
import Header from './components/Header'
import ControlPanel from './components/ControlPanel'
import NetworkVisualization from './components/NetworkVisualization'
import InfoPanel from './components/InfoPanel'
import JobManagement from './components/JobManagement'
import './styles/App.css'

function App() {
  const [selectedNode, setSelectedNode] = useState(null)
  const [clusterData, setClusterData] = useState({
    gpus: [],
    servers: [],
    connections: []
  })

  const [metrics, setMetrics] = useState({
    totalGpus: 0,
    activeConnections: 0,
    avgTemperature: 0
  })

  const handleNodeSelect = (nodeData) => {
    console.log('Node selected:', nodeData)
    setSelectedNode(nodeData)
  }

  const handleRefreshTopology = async () => {
    console.log('Refreshing topology...')
    setSelectedNode(null)
    await loadData()
  }

  useEffect(() => {
    console.log('Component mounted - running initial setup')
    loadData()
  }, [])

  const loadData = async () => {
    try {
      console.log('🔄 Attempting to fetch data from backend...')
      const response = await fetch('http://localhost:8080/api/v1/topology')

      if (response.ok) {
        const backendData = await response.json()
        console.log('✅ Successfully fetched data from backend:', backendData)

        setClusterData(backendData)

        const avgTemp = backendData.gpus.length > 0 
          ? Math.round(
              backendData.gpus.reduce((sum, gpu) => sum + (gpu.temperature || 0), 0) /
              backendData.gpus.length
            )
          : 0

        setMetrics({
          totalGpus: backendData.gpus.length,
          activeConnections: backendData.connections.length,
          avgTemperature: avgTemp
        })
        return
      }
    } catch (error) {
      console.warn('⚠️ Backend not available, using mock data:', error)
    }

    console.log('🎭 Using fallback mock data')
    const mockData = {
      gpus: [
        { id: 'gpu-0', name: 'GPU-0', model: 'RTX 4090', temperature: 72, utilization: 78, status: 'healthy' },
        { id: 'gpu-1', name: 'GPU-1', model: 'RTX 4090', temperature: 75, utilization: 85, status: 'healthy' },
        { id: 'gpu-2', name: 'GPU-2', model: 'RTX 4090', temperature: 78, utilization: 92, status: 'warning' },
        { id: 'gpu-3', name: 'GPU-3', model: 'RTX 4090', temperature: 69, utilization: 67, status: 'healthy' }
      ],
      servers: [
        { id: 'server-1', name: 'Server-1', cpu: 'Intel Xeon Gold', ram: '256GB', status: 'online' },
        { id: 'server-2', name: 'Server-2', cpu: 'Intel Xeon Gold', ram: '256GB', status: 'online' }
      ],
      connections: [
        { id: 'conn-s1-g0', source: 'server-1', target: 'gpu-0', type: 'pcie' },
        { id: 'conn-s1-g1', source: 'server-1', target: 'gpu-1', type: 'pcie' },
        { id: 'conn-s2-g2', source: 'server-2', target: 'gpu-2', type: 'pcie' },
        { id: 'conn-s2-g3', source: 'server-2', target: 'gpu-3', type: 'pcie' },
        { id: 'conn-g0-g1', source: 'gpu-0', target: 'gpu-1', type: 'nvlink' },
        { id: 'conn-g2-g3', source: 'gpu-2', target: 'gpu-3', type: 'nvlink' },
        { id: 'conn-s1-s2', source: 'server-1', target: 'server-2', type: 'infiniband' }
      ]
    }

    setClusterData(mockData)

    const avgTemp = Math.round(
      mockData.gpus.reduce((sum, gpu) => sum + gpu.temperature, 0) / mockData.gpus.length
    )

    setMetrics({
      totalGpus: mockData.gpus.length,
      activeConnections: mockData.connections.length,
      avgTemperature: avgTemp
    })
  }

  return (
    <div className="app">
      <Header />
      
      {/* Main Dashboard - 3 column layout */}
      <main className="main-content">
        <ControlPanel onRefresh={handleRefreshTopology} metrics={metrics} />
        <NetworkVisualization clusterData={clusterData} onNodeSelect={handleNodeSelect} />
        <InfoPanel selectedNode={selectedNode} clusterData={clusterData} />
      </main>
      
      {/* Job Scheduler - Full width below */}
      <section className="scheduler-section">
        <JobManagement clusterData={clusterData} />
      </section>
    </div>
  )
}

export default App
