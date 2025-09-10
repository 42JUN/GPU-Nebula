import React, { useState } from 'react';
import '../styles/JobSubmissionForm.css';

const JobSubmissionForm = ({ onJobSubmitted }) => {
  const [workloadType, setWorkloadType] = useState('inference');
  const [command, setCommand] = useState('');
  const [loading, setLoading] = useState(false);

  const workloadTypes = [
    { value: 'inference', label: '🔮 Inference', desc: 'Run model predictions' },
    { value: 'training', label: '🎯 Training', desc: 'Train new models' },
    { value: 'fine-tuning', label: '⚡ Fine-tuning', desc: 'Adapt existing models' },
    { value: 'testing', label: '🧪 Testing', desc: 'Validate model performance' },
    { value: 'data-processing', label: '📊 Data Processing', desc: 'Process datasets' }
  ];

  const exampleCommands = {
    inference: 'python inference.py --model bert-base --input data.txt',
    training: 'python train.py --model resnet50 --epochs 100 --batch-size 32',
    'fine-tuning': 'python fine_tune.py --base-model gpt-3.5 --dataset custom.json',
    testing: 'python test.py --model saved_model.pt --test-set validation.csv',
    'data-processing': 'python process_data.py --input raw_data/ --output processed/'
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await fetch('/api/v1/jobs/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workload_type: workloadType, command })
      });
      
      const result = await response.json();
      
      if (response.ok) {
        alert(`✅ Job submitted successfully!\nJob ID: ${result.job_id}\nStatus: ${result.status}`);
        setCommand('');
        onJobSubmitted();
      } else {
        alert(`❌ Error: ${result.error || result.message}`);
      }
    } catch (error) {
      alert(`❌ Network Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const useExample = () => {
    setCommand(exampleCommands[workloadType]);
  };

  return (
    <div className="job-submission-form">
      <h3>Submit New AI Workload</h3>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Workload Type:</label>
          <div className="workload-types">
            {workloadTypes.map(type => (
              <label key={type.value} className="workload-option">
                <input
                  type="radio"
                  name="workloadType"
                  value={type.value}
                  checked={workloadType === type.value}
                  onChange={(e) => setWorkloadType(e.target.value)}
                />
                <div className="workload-card">
                  <div className="workload-label">{type.label}</div>
                  <div className="workload-desc">{type.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>
        
        <div className="form-group">
          <div className="command-header">
            <label>Command to Execute:</label>
            <button 
              type="button" 
              onClick={useExample}
              className="example-btn"
            >
              Use Example
            </button>
          </div>
          <textarea
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder={`Enter command for ${workloadType}...`}
            rows={3}
            required
          />
        </div>
        
        <button type="submit" disabled={loading || !command.trim()}>
          {loading ? '⏳ Submitting...' : '🚀 Submit Job'}
        </button>
      </form>
    </div>
  );
};

export default JobSubmissionForm;
