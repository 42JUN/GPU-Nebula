import React, { useState, useEffect } from 'react';
import '../styles/JobManagement.css';

const API_BASE_URL = `http://${window.location.hostname}:8080`;

const JobManagement = ({ clusterData }) => {
  const [jobs, setJobs] = useState([]);
  const [command, setCommand] = useState('');
  const [workloadType, setWorkloadType] = useState('inference');
  const [loading, setLoading] = useState(false);

  const fetchJobs = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/jobs`, {
        cache: 'no-store'
      });
      const data = await response.json();
      setJobs(data.jobs || []);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/jobs/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          workload_type: workloadType, 
          command: command
        })
      });
      
      const result = await response.json();
      
      if (response.ok) {
        alert(`✅ Task assigned to ${result.gpu || 'GPU'}! Job ID: ${result.job_id}`);
        setCommand('');
        fetchJobs();
      } else {
        alert(`❌ Error: ${result.error}`);
      }
    } catch (error) {
      alert(`❌ Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="job-scheduler">
      <div className="scheduler-header">
        <h3>GPU Workload Scheduler</h3>
        <div className="job-stats">
          <span>Total: {jobs.length}</span>
          <span>Running: {jobs.filter(j => j.status === 'running').length}</span>
          <span>Queued: {jobs.filter(j => j.status === 'queued').length}</span>
        </div>
      </div>
      
      <div className="scheduler-content">
        <form onSubmit={handleSubmit} className="job-form">
          <select 
            value={workloadType} 
            onChange={(e) => setWorkloadType(e.target.value)}
            className="workload-select"
          >
            <option value="inference">🔮 Inference</option>
            <option value="training">🎯 Training</option>
            <option value="fine-tuning">⚡ Fine-tuning</option>
            <option value="testing">🧪 Testing</option>
            <option value="data-processing">📊 Data Processing</option>
          </select>
          <input
            type="text"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder="python train.py --epochs 10"
            className="command-input"
            required
          />
          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? '⏳ Assigning...' : ' Assign to GPU'}
          </button>
        </form>

        {jobs.length > 0 && (
          <div className="jobs-preview">
            <h4>Recent Tasks</h4>
            <div className="jobs-grid">
              {jobs.slice(0, 6).map(job => (
                <div key={job.id} className={`job-card ${job.status}`}>
                  <div className="job-header">
                    <span>#{job.id}</span>
                    <span className={`status ${job.status}`}>{job.status}</span>
                  </div>
                  <div className="job-gpu">{job.gpu || 'Assigning...'}</div>
                  <div className="job-command">
                    {job.command?.substring(0, 30)}...
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default JobManagement;
