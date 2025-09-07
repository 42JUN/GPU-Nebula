import { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import '../styles/NetworkVisualization.css'

function NetworkVisualization({ clusterData, onNodeSelect }) {
  const cyRef = useRef(null)
  const cyInstance = useRef(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    console.log('NetworkVisualization useEffect triggered')
    console.log('clusterData:', clusterData)
    console.log('cyRef.current:', cyRef.current)
    
    if (!cyRef.current) {
      console.log('No cyRef.current, setting loading to false')
      setIsLoading(false)
      return
    }

    if (!clusterData || !clusterData.gpus || !clusterData.servers) {
      console.log('No cluster data available, setting loading to false')
      setIsLoading(false)
      return
    }

    try {
      setIsLoading(true)
      setError(null)

      // Destroy existing instance
      if (cyInstance.current) {
        console.log('Destroying existing Cytoscape instance')
        cyInstance.current.destroy()
      }

      // Check if we have data
      const hasData = clusterData.gpus?.length > 0 || clusterData.servers?.length > 0

      console.log('Has data:', hasData)
      console.log('GPUs:', clusterData.gpus?.length || 0)
      console.log('Servers:', clusterData.servers?.length || 0)
      console.log('Connections:', clusterData.connections?.length || 0)

      if (!hasData) {
        setIsLoading(false)
        setError('No network data available')
        return
      }

      // Create elements array
      const elements = [
        // Add GPU nodes
        ...clusterData.gpus.map(gpu => ({
          data: {
            id: gpu.id,
            label: `${gpu.name}\n${gpu.model}`,
            type: 'gpu',
            ...gpu
          }
        })),
        
        // Add server nodes  
        ...clusterData.servers.map(server => ({
          data: {
            id: server.id,
            label: `${server.name}\n${server.cpu}`,
            type: 'server',
            ...server
          }
        })),
        
        // Add connections
        ...clusterData.connections.map(conn => ({
          data: {
            id: conn.id,
            source: conn.source,
            target: conn.target,
            type: conn.type,
            label: conn.type
          }
        }))
      ]

      console.log('Creating Cytoscape with elements:', elements)

      // Initialize Cytoscape
      cyInstance.current = cytoscape({
        container: cyRef.current,
        
        elements: elements,

        style: [
          // GPU nodes
          {
            selector: 'node[type="gpu"]',
            style: {
              'background-color': '#10b981',
              'label': 'data(label)',
              'text-valign': 'center',
              'text-halign': 'center',
              'color': 'white',
              'text-outline-width': 2,
              'text-outline-color': '#000000',
              'width': 140,
              'height': 100,
              'shape': 'round-rectangle',
              'font-size': '16px',
              'font-family': 'Arial, sans-serif',
              'border-width': 3,
              'border-color': '#059669',
              'text-wrap': 'wrap',
              'text-max-width': '130px',
              'text-margin-y': 2,
              'text-margin-x': 2
            }
          },
          
          // Server nodes
          {
            selector: 'node[type="server"]', 
            style: {
              'background-color': '#3b82f6',
              'label': 'data(label)',
              'text-valign': 'center',
              'text-halign': 'center',
              'color': 'white',
              'text-outline-width': 1,
              'text-outline-color': '#000000',
              'width': 160,
              'height': 90,
              'shape': 'round-rectangle',
              'font-size': '16px',
              'font-family': 'Arial, sans-serif',
              'border-color': '#1d4ed8',
              'text-wrap': 'wrap',
              'text-max-width': '150px',
              'text-margin-y': 2,
              'text-margin-x': 2
            }
          },
          
          // Edges/Connections
          {
            selector: 'edge',
            style: {
              'width': 4,
              'line-color': '#fbbf24',
              'target-arrow-color': '#fbbf24',
              'target-arrow-shape': 'triangle',
              'target-arrow-size': 8,
              'curve-style': 'bezier',
              'label': 'data(label)',
              'font-size': '10px',
              'font-weight': 'bold',
              'font-family': 'Arial, sans-serif',
              'color': '#fbbf24',
              'text-outline-width': 1,
              'text-outline-color': '#000000',
              'text-background-color': '#000',
              'text-background-opacity': 0.8,
              'text-background-padding': '4px',
              'text-background-shape': 'roundrectangle'
            }
          },
          
          // Hover effects
          {
            selector: 'node:hover',
            style: {
              'border-width': 4,
              'border-color': '#ffffff',
              'background-color': '#ffffff',
              'color': '#000'
            }
          }
        ],

        layout: {
          name: 'cose',
          animate: true,
          animationDuration: 1000,
          padding: 30,
          nodeOverlap: 20,
          idealEdgeLength: 100,
          edgeElasticity: 100,
          nestingFactor: 5,
          gravity: 80,
          numIter: 1000,
          initialTemp: 200,
          coolingFactor: 0.95,
          minTemp: 1.0
        },

        // Interaction options
        userZoomingEnabled: true,
        userPanningEnabled: true,
        boxSelectionEnabled: false,
        selectionType: 'single'
      })

      console.log('Cytoscape instance created:', cyInstance.current)

      // Add event listeners
      cyInstance.current.on('tap', 'node', (event) => {
        const node = event.target
        const nodeData = node.data()
        console.log('Node clicked:', nodeData)
        onNodeSelect(nodeData)
        
        // Visual feedback
        cyInstance.current.nodes().removeClass('selected')
        node.addClass('selected')
      })

      // Fit to viewport
      setTimeout(() => {
        if (cyInstance.current) {
          cyInstance.current.fit()
          cyInstance.current.center()
          console.log('Cytoscape fitted and centered')
          setIsLoading(false)
        }
      }, 500)

    } catch (err) {
      console.error('Error creating Cytoscape instance:', err)
      setError(`Failed to create network visualization: ${err.message}`)
      setIsLoading(false)
    }

    return () => {
      if (cyInstance.current) {
        console.log('Cleaning up Cytoscape instance')
        cyInstance.current.destroy()
      }
    }
  }, [clusterData, onNodeSelect])

  const handleLayoutChange = (layoutName) => {
    if (!cyInstance.current) return
    
    cyInstance.current.layout({
      name: layoutName,
      animate: true,
      animationDuration: 1000
    }).run()
  }

  const handleZoom = (direction) => {
    if (!cyInstance.current) return
    
    const zoom = cyInstance.current.zoom()
    const newZoom = direction === 'in' ? zoom * 1.2 : zoom / 1.2
    
    cyInstance.current.animate({
      zoom: Math.max(0.1, Math.min(3, newZoom)),
      center: cyInstance.current.center()
    }, {
      duration: 300
    })
  }

  const handleFit = () => {
    if (!cyInstance.current) return
    cyInstance.current.fit()
  }

  return (
    <div className="network-visualization">
      <h2 className="panel-title">🖥️ Network Topology</h2>
      
      <div className="topology-controls">
        <div className="layout-controls">
          <button 
            className="layout-btn active" 
            onClick={() => handleLayoutChange('cose')}
          >
            Auto
          </button>
          <button 
            className="layout-btn" 
            onClick={() => handleLayoutChange('grid')}
          >
            Grid
          </button>
          <button 
            className="layout-btn" 
            onClick={() => handleLayoutChange('circle')}
          >
            Circle
          </button>
          <button 
            className="layout-btn" 
            onClick={() => handleLayoutChange('breadthfirst')}
          >
            Tree
          </button>
        </div>
        
        <div className="zoom-controls">
          <button className="zoom-btn" onClick={() => handleZoom('in')}>+</button>
          <button className="zoom-btn" onClick={handleFit}>⌂</button>
          <button className="zoom-btn" onClick={() => handleZoom('out')}>−</button>
        </div>
      </div>
      
      <div className="graph-container">
        {isLoading && (
          <div className="loading-overlay">
            <div className="loading-spinner"></div>
            <p>Loading network topology...</p>
          </div>
        )}
        
        {error && (
          <div className="loading-overlay">
            <div style={{ color: '#ef4444', fontSize: '16px', marginBottom: '10px' }}>⚠️</div>
            <p style={{ color: '#ef4444' }}>{error}</p>
            <button 
              onClick={() => window.location.reload()} 
              style={{
                marginTop: '16px',
                padding: '8px 16px',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
            >
              Reload Page
            </button>
          </div>
        )}
        
        <div ref={cyRef} className="cytoscape-graph"></div>
        
        <div className="graph-legend">
          <div className="legend-title">Legend</div>
          <div className="legend-items">
            <div className="legend-item">
              <div className="legend-color gpu"></div>
              <span>GPU Nodes</span>
            </div>
            <div className="legend-item">
              <div className="legend-color server"></div>
              <span>Servers</span>
            </div>
            <div className="legend-item">
              <div className="legend-color connection"></div>
              <span>Connections</span>
            </div>
          </div>
        </div>
      </div>
      
      <div className="network-stats">
        <div className="stat-item">
          <span className="stat-value">{clusterData?.gpus?.length || 0}</span>
          <span className="stat-label">GPUs</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{clusterData?.servers?.length || 0}</span>
          <span className="stat-label">Servers</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{clusterData?.connections?.length || 0}</span>
          <span className="stat-label">Links</span>
        </div>
        <div className="stat-item">
          <div className="connection-status">
            <div className="status-dot"></div>
            <span>Online</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default NetworkVisualization