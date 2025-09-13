import subprocess
import psutil
import json
import os
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from create_db import Job, GPU, Agent, History, engine, SessionLocal
import requests

class JobScheduler:
    AGENT_PORT = 8001

    def __init__(self):
        self.session_factory = SessionLocal
    
    def schedule_job(self, workload_type: str, command: str, preferred_gpu: Optional[str] = None) -> dict:
        """Main scheduling function - finds best GPU using temperature and utilization"""
        db = self.session_factory()
        try:
            # If user specified a GPU, use it (unless it's 'auto')
            if preferred_gpu and preferred_gpu != 'auto':
                selected_gpu = db.query(GPU).filter(GPU.id == preferred_gpu).first()
                if not selected_gpu:
                    return {"status": "error", "message": f"GPU {preferred_gpu} not found"}
            else:
                # Smart auto-selection based on temperature and utilization
                selected_gpu = self._find_optimal_gpu(db)
            
            if not selected_gpu:
                # Queue the job for later
                job = Job(
                    workload_type=workload_type,
                    command=command,
                    status="queued"
                )
                db.add(job)
                db.commit()
                
                self._log_job_history(db, job.id, "queued", "No available GPUs, job queued")
                return {"status": "queued", "job_id": job.id, "message": "No GPUs available"}
            
            # Create job record
            job = Job(
                workload_type=workload_type,
                command=command,
                status="pending",
                assigned_gpu_id=selected_gpu.id,
                agent_id=selected_gpu.agent_id
            )
            db.add(job)
            db.commit()
            
            # Launch job
            if self._is_local_gpu(db, selected_gpu):
                success = self._launch_local_job(db, job, selected_gpu)
            else:
                success = self._launch_remote_job(db, job, selected_gpu)
            
            if success:
                job.status = "running"
                job.started_at = datetime.now()
                db.commit()
                self._log_job_history(db, job.id, "started", f"Job running on {selected_gpu.name} (Temp: {selected_gpu.temperature}°C, Util: {selected_gpu.utilization}%)")
                return {
                    "status": "running", 
                    "job_id": job.id, 
                    "gpu": selected_gpu.name,
                    "gpu_temp": selected_gpu.temperature,
                    "gpu_util": selected_gpu.utilization
                }
            else:
                job.status = "failed"
                db.commit()
                self._log_job_history(db, job.id, "failed", "Failed to launch job")
                return {"status": "failed", "job_id": job.id, "error": "Launch failed"}
                
        except Exception as e:
            print(f"Scheduler error: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            db.close()
    
    def _find_optimal_gpu(self, db: Session) -> Optional[GPU]:
        """
        Smart GPU selection algorithm:
        Priority: Lower temperature + Lower utilization + Fewer active jobs
        """
        # Get all healthy, available GPUs
        available_gpus = db.query(GPU).filter(
            GPU.status == "healthy",
            GPU.is_available == True
        ).all()
        
        if not available_gpus:
            return None
        
        # Count active jobs per GPU
        active_jobs_per_gpu = {}
        active_jobs = db.query(Job).filter(Job.status.in_(["running", "pending"])).all()
        
        for job in active_jobs:
            gpu_id = job.assigned_gpu_id
            if gpu_id:
                active_jobs_per_gpu[gpu_id] = active_jobs_per_gpu.get(gpu_id, 0) + 1
        
        # Score each GPU (lower score = better)
        best_gpu = None
        best_score = float('inf')
        
        for gpu in available_gpus:
            score = self._calculate_gpu_priority_score(gpu, active_jobs_per_gpu.get(gpu.id, 0))
            
            print(f"GPU {gpu.name}: Score={score:.2f} (Temp: {gpu.temperature}°C, Util: {gpu.utilization}%, Jobs: {active_jobs_per_gpu.get(gpu.id, 0)})")
            
            if score < best_score:
                best_score = score
                best_gpu = gpu
        
        if best_gpu:
            print(f"✅ Selected GPU: {best_gpu.name} with score {best_score:.2f}")
        
        return best_gpu
    
    def _calculate_gpu_priority_score(self, gpu: GPU, active_jobs_count: int) -> float:
        """
        Calculate priority score for GPU selection
        Lower score = higher priority
        
        Factors:
        1. Temperature (weight: 2.0) - cooler GPUs preferred
        2. Utilization (weight: 3.0) - less utilized GPUs preferred  
        3. Active jobs (weight: 5.0) - GPUs with fewer jobs preferred
        4. Memory usage (weight: 1.5) - GPUs with more free memory preferred
        """
        
        # Temperature score (0-100, but penalize high temps more)
        temp = gpu.temperature or 50
        if temp > 80:
            temp_score = temp * 2  # Heavy penalty for hot GPUs
        else:
            temp_score = temp
        
        # Utilization score (0-100)
        util_score = gpu.utilization or 0
        
        # Active jobs score (exponential penalty)
        jobs_score = active_jobs_count * 20  # Heavy penalty for multiple jobs
        
        # Memory usage score
        if gpu.memory_total and gpu.memory_used:
            memory_usage_pct = (gpu.memory_used / gpu.memory_total) * 100
        else:
            memory_usage_pct = 50  # Default assumption
        
        # Calculate weighted total score
        total_score = (
            temp_score * 2.0 +      # Temperature weight
            util_score * 3.0 +      # Utilization weight  
            jobs_score * 5.0 +      # Job count weight (highest)
            memory_usage_pct * 1.5  # Memory usage weight
        )
        
        return total_score
    
    def _is_local_agent(self, db: Session, agent_id: int) -> bool:
        """
        Check if the agent_id corresponds to an agent running on the local machine.
        This is more robust than checking for a single hostname.
        """
        import socket
        hostname = socket.gethostname()
        # An agent is local if its hostname contains the local machine's hostname.
        # This covers both the main agent and the self-detected agent.
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return False
        return hostname in agent.hostname

    def _is_local_gpu(self, db: Session, gpu: GPU) -> bool:
        return self._is_local_agent(db, gpu.agent_id)
    
    def _launch_local_job(self, db: Session, job: Job, gpu: GPU) -> bool:
        """Launch job on local GPU using subprocess"""
        try:
            import shlex
            # Extract GPU index from its ID (e.g., "GPU-0" -> 0)
            try:
                gpu_index = int(gpu.id.split('-')[-1])
            except (ValueError, IndexError):
                gpu_index = 0  # Fallback
            
            # Set CUDA device and launch
            env = {
                **os.environ,
                'CUDA_VISIBLE_DEVICES': str(gpu_index)
            }
            
            process = subprocess.Popen(
                shlex.split(job.command),
                shell=False,  # Important for security
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd="c:/dev/GPU-Nebula/backend/"
            )
            
            job.pid = process.pid
            db.commit()
            print(f"✅ Launched job {job.id} with PID {process.pid} on GPU {gpu_index} ({gpu.name})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to launch local job: {e}")
            return False
    
    def _launch_remote_job(self, db: Session, job: Job, gpu: GPU) -> bool:
        """Launch job on remote agent via API"""
        try:
            import requests
            agent = gpu.agent
            
            payload = {
                "job_id": job.id,
                "command": job.command,
                "gpu_id": gpu.id,
                "workload_type": job.workload_type
            }
            
            response = requests.post(
                f"http://{agent.ip_address}:8001/agent/run-job",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                job.pid = result.get("pid")
                db.commit()
                return True
            else:
                print(f"Remote launch failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"Failed to launch remote job: {e}")
            return False
    
    def _log_job_history(self, db: Session, job_id: int, action: str, details: str):
        """Log job event to history"""
        history = History(
            job_id=job_id,
            action=action,
            details=details
        )
        db.add(history)
        db.commit()
    
    def monitor_jobs(self):
        """Background task to monitor running jobs, both local and remote."""
        db = self.session_factory()
        try:
            running_jobs = db.query(Job).filter(Job.status == "running").all()
            
            for job in running_jobs:
                if not job.pid:
                    continue

                is_local = self._is_local_agent(db, job.agent_id)

                if is_local:
                    # Monitor local job using psutil
                    try:
                        process = psutil.Process(job.pid)
                        if not process.is_running():
                            job.status = "completed"
                            job.finished_at = datetime.now()
                            self._log_job_history(db, job.id, "completed", "Job process finished.")
                    except psutil.NoSuchProcess:
                        job.status = "completed"  # Assume completed if process is gone
                        job.finished_at = datetime.now()
                        self._log_job_history(db, job.id, "completed", "Job process not found, assuming completed.")
                else:
                    # Monitor remote job via agent's API
                    agent = job.agent
                    if not agent:
                        continue
                    
                    try:
                        response = requests.get(
                            f"http://{agent.ip_address}:{self.AGENT_PORT}/agent/job-status/{job.pid}",
                            timeout=5
                        )
                        if response.status_code == 200:
                            status_data = response.json()
                            if status_data.get("status") in ["not_running", "not_found"]:
                                job.status = "completed"
                                job.finished_at = datetime.now()
                                self._log_job_history(db, job.id, "completed", f"Remote job finished on {agent.hostname}.")
                        else:
                            print(f"⚠️ Could not get job status for {job.id} from agent {agent.hostname}. Status: {response.status_code}")
                    except requests.RequestException as e:
                        print(f"⚠️ Error contacting agent {agent.hostname} to monitor job {job.id}: {e}")
            
            db.commit()
        finally:
            db.close()
    
    def get_job_status(self, job_id: int) -> dict:
        """Get current status of a job"""
        db = self.session_factory()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return {"error": "Job not found"}
            
            return {
                "id": job.id,
                "status": job.status,
                "workload_type": job.workload_type,
                "command": job.command,
                "gpu": job.gpu.name if job.gpu else None,
                "agent": job.agent.hostname if job.agent else None,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None
            }
        finally:
            db.close()
    
    def list_jobs(self, limit: int = 50) -> List[dict]:
        """List recent jobs"""
        db = self.session_factory()
        try:
            jobs = db.query(Job).order_by(Job.created_at.desc()).limit(limit).all()
            
            return [{
                "id": job.id,
                "workload_type": job.workload_type,
                "status": job.status,
                "gpu": job.gpu.name if job.gpu else None,
                "agent": job.agent.hostname if job.agent else None,
                "created_at": job.created_at.isoformat(),
                "command": job.command[:100] + "..." if len(job.command) > 100 else job.command
            } for job in jobs]
        finally:
            db.close()

# Global scheduler instance
scheduler = JobScheduler()
