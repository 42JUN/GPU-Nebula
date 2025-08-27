import { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import '../styles/NetworkVisualization.css'

function NetworkVisualization({ clusterData, onNodeSelect }) {
  const cyRef = useRef(null)
  const cyInstance = useRef(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!cyRef.current) return

    setIsLoading(true)

    if (cyInstance.current) {
      cyInstance.current.destroy()
    }

    cyInstance.current = cytoscape({
      container: cyRef.current,
      
      elements: [
        ...clusterData.gpus.map(gpu => ({
          data: {
            id: gpu.id,
            label: `${gpu.name}\n${gpu.model}`,
            type: 'gpu',
            ...gpu
          }
        })),
        
        ...clusterData.servers.map(server => ({
          data: {
            id: server.id,
            label: server.name,
            type: 'server',
            ...server
          }
        })),
        
        ...clusterData.connections.map(conn => ({
          data: {
            id: conn.id,
            source: conn.source,
            target: conn.target,
            type: conn.type
          }
        }))
      ],

      style: [
        {
          selector: 'node[type="gpu"]',
          style: {
            'background-color': '#4CAF50',
            'label': 'data(label)',
            'text-valign': 'center',
            'color': 'white',
            'width': 80,
            'height': 60,
            'shape': 'round-rectangle'
          }
        },
        {
          selector: 'node[type="server"]',
          style: {
            'background-color': '#2196F3',
            'label': 'data(label)',
            'text-valign': 'center',
            'color': 'white',
            'width': 120,
            'height': 50,
            'shape': 'round-rectangle'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 4,
            'line-color': '#FF6B35',
            'target-arrow-color': '#FF6B35',
            'target-arrow-shape': 'triangle'
          }
        }
      ],

      layout: {
        name: 'cose',
        animate: true
      }
    })

    cyInstance.current.on('tap', 'node', (event) => {
      const node = event.target
      const nodeData = node.data()
      onNodeSelect(nodeData)
    })

    setTimeout(() => setIsLoading(false), 1000)

    return () => {
      if (cyInstance.current) {
        cyInstance.current.destroy()
      }
    }
  }, [clusterData, onNodeSelect])

  return (
    <div className="network-visualization">
      <h2 className="panel-title">🖥️ Network Topology</h2>
      
      <div className="graph-container">
        {isLoading && (
          <div className="loading-overlay">
            <div className="loading-spinner"></div>
            <p>Loading topology...</p>
          </div>
        )}
        
        <div ref={cyRef} className="cytoscape-graph"></div>
      </div>
    </div>
  )
}

export default NetworkVisualization