from typing import List, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from gpu_detector import GPUDetector
import traceback
from datetime import datetime
import psutil

# --- Database and ORM ---
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from create_db import GPU, Network, Job, History, Agent, Base, create_tables, SessionLocal

# --- Scheduler Import ---
from scheduler import scheduler

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 GPU Nebula Control Plane is starting up...")
    create_tables()
    print("✅ Control Plane is ready.")
    yield
    print("👋 GPU Nebula Control Plane is shutting down.")

# --- App Initialization ---
app = FastAPI(
    title="GPU Nebula Control Plane", 
    version="2.1.0", 
    description="Central management API for a distributed GPU cluster with job scheduling.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in dev (restrict later for prod)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Connection ---
DATABASE_URL = "sqlite:///c:/dev/GPU-Nebula/backend/control_plane.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Models ---
class AgentInfo(BaseModel):
    hostname: str
    ip_address: str
    os: str

class GPUReport(BaseModel):
    gpus: List[Dict[str, Any]]
    servers: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    detection_method: str
    status: str

class AgentReportIn(BaseModel):
    agent_info: AgentInfo
    gpu_report: GPUReport

class JobRequest(BaseModel):
    workload_type: str  # inference, training, fine-tuning, etc.
    command: str        # The command to execute

# --- Agent API Router ---
agent_router = APIRouter(prefix="/api/v1/agent", tags=["Agent Communication"])

@agent_router.post("/report-in")
def agent_report_in(report: AgentReportIn, db: Session = Depends(get_db)):
    """Endpoint for agents to report their status and detected GPUs."""
    try:
        # 1. Upsert Agent
        agent = db.query(Agent).filter_by(hostname=report.agent_info.hostname).first()
        if agent:
            agent.ip_address = report.agent_info.ip_address
            agent.os = report.agent_info.os
        else:
            agent = Agent(**report.agent_info.dict())
            db.add(agent)
            db.flush()  # get agent.id

        # 2. Clear old GPUs for this agent (avoid duplicates)
        db.query(GPU).filter_by(agent_id=agent.id).delete()

        # 3. Insert GPUs from report
        gpus_added = 0
        for gpu_data in report.gpu_report.gpus:
            gpu = GPU(
                id=gpu_data.get("id"),
                name=gpu_data.get("name"),
                model=gpu_data.get("model"),
                status=gpu_data.get("status"),
                temperature=gpu_data.get("temperature", 0),
                utilization=gpu_data.get("utilization", 0),
                memory_total=gpu_data.get("memoryTotal", 0),
                memory_used=gpu_data.get("memoryUsed", 0),
                agent_id=agent.id,
                vram=gpu_data.get("memoryTotal", 0) // (1024**3),
            )
            db.add(gpu)
            gpus_added += 1

        db.commit()
        return {"message": f"Report from {agent.hostname} processed. GPUs Added: {gpus_added}."}

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- User-Facing API Router ---
api_router = APIRouter(prefix="/api/v1", tags=["Cluster Management"])

@api_router.get("/topology")
def get_cluster_topology(db: Session = Depends(get_db)):
    """Get the entire cluster topology formatted for the frontend."""
    agents = db.query(Agent).all()
    active_jobs = db.query(Job).filter(Job.status.in_(["running", "pending"])).all()

    gpus, servers, connections = [], [], []

    for agent in agents:
        servers.append({
            "id": f"server-{agent.hostname}",
            "name": agent.hostname,
            "cpu": "Unknown",
            "ram": "Unknown",
            "os": agent.os,
            "status": "healthy",
            "active_jobs": len([j for j in active_jobs if j.agent_id == agent.id])
        })

        db_gpus = db.query(GPU).filter_by(agent_id=agent.id).all()
        for gpu in db_gpus:
            # Check if this GPU has active jobs
            gpu_jobs = [j for j in active_jobs if j.assigned_gpu_id == gpu.id]
            
            gpus.append({
                "id": str(gpu.id),
                "name": gpu.name or f"GPU-{gpu.id}",
                "model": gpu.model,
                "status": gpu.status,
                "temperature": gpu.temperature,
                "utilization": gpu.utilization,
                "memory_total": gpu.memory_total,
                "memory_used": gpu.memory_used,
                "active_jobs": len(gpu_jobs),
                "current_job": gpu_jobs[0].workload_type if gpu_jobs else None
            })
            connections.append({
                "id": f"conn-{agent.hostname}-{gpu.id}",
                "source": f"server-{agent.hostname}",
                "target": str(gpu.id),
                "type": "pcie"
            })

    return {
        "gpus": gpus, 
        "servers": servers, 
        "connections": connections,
        "total_jobs": len(active_jobs)
    }

# --- Job Management Endpoints ---
@api_router.post("/jobs/submit")
def submit_job(job_request: JobRequest, db: Session = Depends(get_db)):
    """Submit a new job for GPU scheduling"""
    try:
        result = scheduler.schedule_job(job_request.workload_type, job_request.command)
        return result
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@api_router.get("/jobs/{job_id}/status")
def get_job_status(job_id: int):
    """Get the current status of a job"""
    try:
        result = scheduler.get_job_status(job_id)
        if "error" in result:
            return JSONResponse(status_code=404, content=result)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@api_router.get("/jobs")
def list_jobs():
    """List all jobs with their current status"""
    try:
        return {"jobs": scheduler.list_jobs()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@api_router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: int, db: Session = Depends(get_db)):
    """Cancel a running job"""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            return JSONResponse(status_code=404, content={"error": "Job not found"})
        
        if job.status == "running" and job.pid:
            try:
                process = psutil.Process(job.pid)
                process.terminate()
                job.status = "cancelled"
                job.finished_at = datetime.now()
                db.commit()
                return {"status": "cancelled", "job_id": job_id}
            except psutil.NoSuchProcess:
                job.status = "failed"
                job.finished_at = datetime.now()
                db.commit()
                return {"status": "already_finished", "job_id": job_id}
        else:
            return {"status": job.status, "job_id": job_id, "message": "Job not running"}
            
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@api_router.get("/jobs/{job_id}/history")
def get_job_history(job_id: int, db: Session = Depends(get_db)):
    """Get the history/logs of a specific job"""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return JSONResponse(status_code=404, content={"error": "Job not found"})
        
        history = db.query(History).filter(History.job_id == job_id).order_by(History.timestamp.desc()).all()
        
        return {
            "job_id": job_id,
            "history": [{
                "id": h.id,
                "action": h.action,
                "details": h.details,
                "timestamp": h.timestamp.isoformat()
            } for h in history]
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@api_router.post("/jobs/monitor")
def monitor_jobs_now():
    """Manually trigger job monitoring"""
    try:
        scheduler.monitor_jobs()
        return {"status": "success", "message": "Job monitoring completed"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- UI Interaction Endpoints ---
SELF_GPU_AGENT_HOSTNAME = "localhost-browser-detected"

@app.post("/gpu/detect", tags=["UI Interaction"])
def detect_self_gpu(db: Session = Depends(get_db)):
    try:
        detector = GPUDetector()
        report_data = detector.detect_gpus()

        if report_data['status'] == 'mock' or not report_data.get('gpus'):
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "No GPUs detected on the server."}
            )

        agent = db.query(Agent).filter_by(hostname=SELF_GPU_AGENT_HOSTNAME).first()
        if not agent:
            agent = Agent(
                hostname=SELF_GPU_AGENT_HOSTNAME,
                ip_address="127.0.0.1",
                os="Control Plane Host"
            )
            db.add(agent)
            db.flush()

        db.query(GPU).filter_by(agent_id=agent.id).delete()

        for gpu_data in report_data["gpus"]:
            filtered_data = {k: v for k, v in gpu_data.items() if k in GPU.__table__.columns}
            gpu = GPU(**filtered_data)
            gpu.agent_id = agent.id
            gpu.vram = gpu_data.get("memoryTotal", 0) // (1024**3)
            gpu.memory_total = gpu_data.get("memoryTotal", 0)
            gpu.memory_used = gpu_data.get("memoryUsed", 0)
            db.add(gpu)
        
        db.commit()

        return {
            "status": "success",
            "gpus": report_data["gpus"],
            "detection_method": report_data["detection_method"],
            "message": f"Detected {len(report_data['gpus'])} GPU(s) on the server."
        }
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/gpu/self", tags=["UI Interaction"])
def get_self_gpu(db: Session = Depends(get_db)):
    agent = db.query(Agent).filter_by(hostname=SELF_GPU_AGENT_HOSTNAME).first()
    gpu = db.query(GPU).filter_by(agent_id=agent.id).first() if agent else None
    return {"gpu": {c.name: getattr(gpu, c.name) for c in gpu.__table__.columns} if gpu else None}

# --- Register Routers ---
app.include_router(agent_router)
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=False)
