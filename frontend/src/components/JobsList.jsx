import React from 'react';

const API_BASE_URL = `http://${window.location.hostname}:8080`;

const JobsList = ({ jobs, onJobAction }) => {
  const cancelJob = async (jobId) => {
    if (!confirm('Are you sure you want to cancel this job?')) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/cancel`, {
        method: 'POST'
      });
      
      if (response.ok) {
        alert('✅ Job cancelled successfully');
        onJobAction();
      } else {
        const result = await response.json();
        alert(`❌ Error: ${result.error}`);
      }
    } catch (error) {
      alert(`❌ Error cancelling job: ${error.message}`);
    }
  };

  const getStatusIcon = (status) => {
    const icons = {
      pending: '⏳',
      queued: '📋',
      running: '🏃‍♂️',
      completed: '✅',
      failed: '❌',
      cancelled: '🚫'
    };
    return icons[status] || '❓';
  };

  const formatDuration = (start, end) => {
    if (!start) return 'N/A';
    const startTime = new Date(start);
    const endTime = end ? new Date(end) : new Date();
    const duration = Math.floor((endTime - startTime) / 1000);
    
    if (duration < 60) return `${duration}s`;
    if (duration < 3600) return `${Math.floor(duration / 60)}m ${duration % 60}s`;
    return `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`;
  };

  if (jobs.length === 0) {
    return (
      <div className="jobs-list">
        <h3>📋 Job Queue</h3>
        <div className="empty-jobs">
          <p>No jobs submitted yet</p>
          <small>Submit your first AI workload above!</small>
        </div>
      </div>
    );
  }

  return (
    <div className="jobs-list">
      <h3>📋 Job Queue ({jobs.length})</h3>
      
      <div className="jobs-table-container">
        <table className="jobs-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>Status</th>
              <th>GPU</th>
              <th>Agent</th>
              <th>Duration</th>
              <th>Command</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map(job => (
              <tr key={job.id} className={`job-row ${job.status}`}>
                <td><strong>#{job.id}</strong></td>
                <td>
                  <span className="workload-type">{job.workload_type}</span>
                </td>
                <td>
                  <span className={`status-badge ${job.status}`}>
                    {getStatusIcon(job.status)} {job.status}
                  </span>
                </td>
                <td>{job.gpu || '⏳'}</td>
                <td>{job.agent || '⏳'}</td>
                <td>
                  {formatDuration(job.created_at, job.finished_at)}
                </td>
                <td>
                  <code className="command-preview" title={job.command}>
                    {job.command.length > 50 
                      ? `${job.command.substring(0, 50)}...` 
                      : job.command}
                  </code>
                </td>
                <td>
                  <div className="job-actions">
                    {(job.status === 'running' || job.status === 'pending') && (
                      <button 
                        onClick={() => cancelJob(job.id)}
                        className="action-btn cancel-btn"
                        title="Cancel Job"
                      >
                        🚫
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default JobsList;
