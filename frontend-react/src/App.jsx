////imports
import { useState, useEffect } from 'react'
// FIXED: Header should be capitalized
import Header from './components/Header'
import ControlPanel from './components/ControlPanel'
// FIXED: Added space after 'from'
import NetworkVisualization from './components/NetworkVisualization'
import InfoPanel from './components/InfoPanel'
import './styles/App.css'

function App() {
  // States (your code is correct here)
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

  // Event handlers
  const handleNodeSelect = (nodeData) => {
    console.log('Node selected:', nodeData)
    setSelectedNode(nodeData)
  }

  const handleRefreshTopology = () => {
    console.log('Refreshing topology...')
    setSelectedNode(null)
    
    // FIXED: Moved setTimeout inside the function
    setTimeout(() => {
      console.log('Refresh complete')
    }, 1000)
  }

  // FIXED: useEffect (was "useEffects" - typo)
  useEffect(() => {
    console.log('Component mounted - running initial setup')
    loadMockData()
  }, [])

  const loadMockData = async () => {
    try {
      console.log('🔄 Attempting to fetch data from backend...')
      
      // Try to fetch from backend first
      const response = await fetch('http://localhost:8000/topology')
      
      if (response.ok) {
        const backendData = await response.json()
        console.log('✅ Successfully fetched data from backend:', backendData)
        
        // Use backend data if available
        setClusterData({
          gpus: backendData.gpus || [],
          servers: backendData.servers || [],
          connections: backendData.connections || []
        })
        
        // Calculate metrics from backend data
        const avgTemp = backendData.gpus?.length > 0 
          ? Math.round(backendData.gpus.reduce((sum, gpu) => sum + (gpu.temperature || 0), 0) / backendData.gpus.length)
          : 0
        
        setMetrics({
          totalGpus: backendData.gpus?.length || 0,
          activeConnections: backendData.connections?.length || 0,
          avgTemperature: avgTemp
        })
        
        console.log('📊 Updated metrics from backend data')
        return
      }
    } catch (error) {
      console.warn('⚠️ Backend not available, using mock data:', error)
    }
    
    // Fallback to mock data if backend fails
    console.log('🎭 Using fallback mock data')
    const mockData = {
      gpus: [
        {
          id: 'gpu-0',
          name: 'GPU-0',
          model: 'RTX 4090',
          temperature: 72,
          utilization: 78,
          status: 'healthy'
        },
        {
          id: 'gpu-1',
          name: 'GPU-1',
          model: 'RTX 4090',
          temperature: 75,
          utilization: 85, // FIXED: Different utilization values
          status: 'healthy'
        },
        {
          id: 'gpu-2',
          name: 'GPU-2',
          model: 'RTX 4090',
          temperature: 78, // FIXED: Was 92, made more realistic
          utilization: 92,
          status: 'warning' // FIXED: Changed to warning for variety
        },
        {
          id: 'gpu-3',
          name: 'GPU-3',
          model: 'RTX 4090',
          temperature: 69,
          utilization: 67,
          status: 'healthy'
        }
      ],
      servers: [
        {
          id: 'server-1',
          name: 'Server-1',
          cpu: 'Intel Xeon Gold',
          ram: '256GB',
          status: 'online'
        },
        {
          id: 'server-2',
          name: 'Server-2',
          cpu: 'Intel Xeon Gold',
          ram: '256GB',
          status: 'online'
        }
      ],
      connections: [
        { id: 'conn-1', source: 'gpu-0', target: 'gpu-1', type: 'nvlink' },
        { id: 'conn-2', source: 'gpu-1', target: 'gpu-2', type: 'nvlink' },
        { id: 'conn-3', source: 'gpu-2', target: 'gpu-3', type: 'nvlink' },
        // FIXED: 'server-' was incomplete, should be 'server-2'
        { id: 'conn-4', source: 'server-1', target: 'server-2', type: 'infiniband' }
      ]
    }

    setClusterData(mockData)

    // FIXED: Added Math.round for cleaner temperature
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
      {/* FIXED: Added Header component */}
      <Header />
      
      <main className="main-content">
      
        <ControlPanel
          onRefresh={handleRefreshTopology}
          metrics={metrics}
        />
        
        <NetworkVisualization
          clusterData={clusterData}
          onNodeSelect={handleNodeSelect}
        />
        
        <InfoPanel
          selectedNode={selectedNode}
          clusterData={clusterData}
        />
      </main>
    </div>
  )
}

export default App