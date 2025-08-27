import '../styles/InfoPanel.css'

function InfoPanel({ selectedNode, clusterData }) {
  
  const renderGPUDetails = (gpu) => (
    <div className="node-details">
      <h3>🖥️ {gpu.name}</h3>
      <div className="details-grid">
        <div className="detail-item">
          <span className="detail-label">Model:</span>
          <span className="detail-value">{gpu.model}</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Temperature:</span>
          <span className="detail-value">{gpu.temperature}°C</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Utilization:</span>
          <span className="detail-value">{gpu.utilization}%</span>
        </div>
      </div>
    </div>
  )

  const renderServerDetails = (server) => (
    <div className="node-details">
      <h3>🖥️ {server.name}</h3>
      <div className="details-grid">
        <div className="detail-item">
          <span className="detail-label">CPU:</span>
          <span className="detail-value">{server.cpu}</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">RAM:</span>
          <span className="detail-value">{server.ram}</span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="info-panel">
      <h2 className="panel-title">📊 Component Details</h2>
      
      <div className="info-content">
        {selectedNode ? (
          selectedNode.type === 'gpu' ? 
            renderGPUDetails(selectedNode) : 
            renderServerDetails(selectedNode)
        ) : (
          <div className="no-selection">
            <p>👆 Click on a GPU or server to view details</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default InfoPanel