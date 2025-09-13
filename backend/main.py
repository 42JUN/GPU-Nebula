from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from gpu_detector import GPUDetector
import traceback
from datetime import datetime
import psutil
import requests
import logging
import socket

# --- Database and ORM ---
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from create_db import GPU, Network, Job, History, Agent, Base, create_tables, SessionLocal

# --- Scheduler Import ---
from scheduler import scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Configuration ---
DATABASE_URL = "sqlite:///c:/dev/GPU-Nebula/backend/control_plane.db"
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,   # Recycle connections every hour
    echo=False  # Set to True for SQL debugging
)

# --- Dependency Management ---
def get_db():
    """FastAPI dependency for database sessions with proper error handling"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def get_local_ip():
    """Get local IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't have to be reachable
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 GPU Nebula Control Plane is starting up...")
    try:
        create_tables()
        logger.info("✅ Control Plane is ready.")
        yield
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise
    finally:
        logger.info("👋 GPU Nebula Control Plane is shutting down.")

# --- App Initialization ---
app = FastAPI(
    title="GPU Nebula Control Plane", 
    version="2.1.0", 
    description="Central management API for a distributed GPU cluster with job scheduling.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    # Allow all origins for simplicity, as we are not using cookie-based authentication.
    # This is more robust for handling requests from both browsers and scripts (like the agent).
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class AgentInfo(BaseModel):
    hostname: str
    ip_address: str
    os: str
    
    @validator('hostname')
    def validate_hostname(cls, v):
        if not v or not v.strip():
            raise ValueError('Hostname cannot be empty')
        return v.strip()
    
    @validator('ip_address')
    def validate_ip(cls, v):
        if not v or not v.strip():
            raise ValueError('IP address cannot be empty')
        return v.strip()

class GPUReport(BaseModel):
    gpus: List[Dict[str, Any]]
    servers: List[Dict[str, Any]] = []
    connections: List[Dict[str, Any]] = []
    detection_method: str
    status: str

class AgentReportIn(BaseModel):
    agent_info: AgentInfo
    gpu_report: GPUReport

class JobRequest(BaseModel):
    workload_type: str
    command: str
    preferred_gpu: Optional[str] = None
    
    @validator('workload_type')
    def validate_workload_type(cls, v):
        if not v or not v.strip():
            raise ValueError('Workload type cannot be empty')
        return v.strip()
    
    @validator('command')
    def validate_command(cls, v):
        if not v or not v.strip():
            raise ValueError('Command cannot be empty')
        return v.strip()

# --- Error Handlers ---
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc):
    logger.error(f"Database error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Database operation failed", "detail": str(exc)}
    )

@app.exception_handler(OperationalError)
async def operational_error_handler(request, exc):
    logger.error(f"Database connection error: {exc}")
    return JSONResponse(
        status_code=503,
        content={"error": "Database connection error", "detail": "Service temporarily unavailable"}
    )

# --- Agent API Router ---
agent_router = APIRouter(prefix="/api/v1/agent", tags=["Agent Communication"])

@agent_router.post("/report-in")
def agent_report_in(report: AgentReportIn, request: Request, db: Session = Depends(get_db)):
    """Endpoint for agents to report their status and detected GPUs."""
    try:
        # Log incoming request headers for debugging
        client_host = request.client.host if request.client else "unknown"
        logger.info(f"Received report from agent: {report.agent_info.hostname} ({client_host})")
        logger.debug(f"Request headers: {request.headers}")
        
        # Validate report data
        if not report.gpu_report.gpus:
            logger.warning(f"Agent {report.agent_info.hostname} reported no GPUs")
        
        # 1. Upsert Agent
        agent = db.query(Agent).filter_by(hostname=report.agent_info.hostname).first()
        if agent:
            agent.ip_address = report.agent_info.ip_address
            agent.os = report.agent_info.os
            agent.last_seen = datetime.now()
        else:
            agent = Agent(
                hostname=report.agent_info.hostname,
                ip_address=report.agent_info.ip_address,
                os=report.agent_info.os,
                last_seen=datetime.now()
            )
            db.add(agent)
            db.flush()  # Get agent.id

        # 2. Clear old GPUs for this agent
        old_gpu_count = db.query(GPU).filter_by(agent_id=agent.id).count()
        db.query(GPU).filter_by(agent_id=agent.id).delete()

        # 3. Insert new GPUs
        gpus_added = 0
        for gpu_data in report.gpu_report.gpus:
            try:
                gpu = GPU(
                    id=gpu_data.get("id"),
                    name=gpu_data.get("name", "Unknown GPU"),
                    model=gpu_data.get("model", "Unknown Model"),
                    status=gpu_data.get("status", "unknown"),
                    temperature=gpu_data.get("temperature", 0),
                    utilization=gpu_data.get("utilization", 0),
                    memory_total=gpu_data.get("memoryTotal", 0),
                    memory_used=gpu_data.get("memoryUsed", 0),
                    agent_id=agent.id,
                    vram=gpu_data.get("memoryTotal", 0) // (1024**3) if gpu_data.get("memoryTotal") else 0,
                    is_available=gpu_data.get("status") == "healthy",
                    pci_bus_id=gpu_data.get("pci_bus_id", "")
                )
                db.add(gpu)
                gpus_added += 1
            except Exception as e:
                logger.error(f"Error adding GPU {gpu_data.get('id', 'unknown')}: {e}")
                continue

        db.commit()
        
        logger.info(f"Report processed: {agent.hostname}, GPUs: {old_gpu_count} -> {gpus_added}")
        return {
            "status": "success",
            "message": f"Report from {agent.hostname} processed successfully",
            "gpus_added": gpus_added,
            "gpus_removed": old_gpu_count
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing agent report: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500, 
            content={"status": "error", "error": str(e)}
        )

# --- User-Facing API Router ---
api_router = APIRouter(prefix="/api/v1", tags=["Cluster Management"])

@api_router.get("/topology")
def get_cluster_topology(db: Session = Depends(get_db)):
    """Get the entire cluster topology formatted for the frontend."""
    try:
        agents = db.query(Agent).all()
        active_jobs = db.query(Job).filter(Job.status.in_(["running", "pending"])).all()
        
        logger.info(f"Found {len(agents)} agents in database")
        for agent in agents:
            logger.info(f"Agent: {agent.hostname} - IP: {agent.ip_address} - Last seen: {agent.last_seen}")

        gpus, servers, connections = [], [], []
        other_agents = []
        control_plane_hostname = None
        
        # Process each agent and create server nodes
        for agent in agents:
            # Determine if this is the control plane
            is_control_plane = any(keyword in agent.hostname.lower() for keyword in [
                'dell', 'control', 'localhost', 'browser-detected', 'master', 'gpu-detected'
            ])
            
            if is_control_plane and not control_plane_hostname:
                # This is the first agent we've found that looks like the control plane.
                control_plane_hostname = agent.hostname
                servers.append(agent) # Add the full agent object to process first
            else:
                other_agents.append(agent)

        # If no agent was identified as the control plane, create a virtual one.
        if not control_plane_hostname:
            actual_hostname = socket.gethostname()
            hub_hostname = f"{actual_hostname}-ControlPlane"
            
            # Add the virtual control plane node to the front of the servers list
            servers.insert(0, {
                "id": f"server-{hub_hostname}",
                "name": hub_hostname,
                "cpu": "Unknown",
                "ram": "Unknown",
                "os": "Control Plane",
                "status": "healthy",
                "active_jobs": 0,
                "ip_address": get_local_ip(),
                "last_seen": datetime.now().isoformat(),
                "is_control_plane": True,
                "is_virtual": True # Mark this as a virtual node
            })
        else:
            # An existing agent was designated as the control plane.
            hub_hostname = control_plane_hostname

        # Now, process all other agents
        servers.extend(other_agents)

        # --- Build final topology from sorted server list ---
        final_servers = []
        for agent_or_node in servers:
            is_virtual = isinstance(agent_or_node, dict) and agent_or_node.get("is_virtual")
            
            if is_virtual:
                final_servers.append(agent_or_node)
                continue

            # This is a real agent from the database
            agent = agent_or_node
            
            # Calculate status based on last_seen
            status = "healthy"
            if agent.last_seen:
                time_diff = (datetime.now() - agent.last_seen).total_seconds()
                status = "healthy" if time_diff < 300 else "offline"  # 5 minutes timeout
            
            # Count active jobs for this agent
            server_active_jobs = [j for j in active_jobs if j.agent_id == agent.id]
            
            # Add server node
            final_servers.append({
                "id": f"server-{agent.hostname}",
                "name": agent.hostname,
                "cpu": "Unknown",
                "ram": "Unknown", 
                "os": agent.os or "Unknown",
                "status": status,
                "active_jobs": len(server_active_jobs),
                "ip_address": agent.ip_address,
                "last_seen": agent.last_seen.isoformat() if agent.last_seen else None,
                "is_control_plane": agent.hostname == hub_hostname
            })

            # Add GPU information for this agent
            db_gpus = db.query(GPU).filter_by(agent_id=agent.id).all()
            logger.info(f"Agent {agent.hostname} has {len(db_gpus)} GPUs")
            
            for gpu in db_gpus:
                gpu_jobs = [j for j in active_jobs if j.assigned_gpu_id == gpu.id]
                
                gpus.append({
                    "id": str(gpu.id),
                    "name": gpu.name or f"GPU-{gpu.id}",
                    "model": gpu.model or "Unknown",
                    "status": gpu.status or "unknown",
                    "temperature": gpu.temperature or 0,
                    "utilization": gpu.utilization or 0,
                    "memory_total": gpu.memory_total or 0,
                    "memory_used": gpu.memory_used or 0,
                    "memory_free": max(0, (gpu.memory_total or 0) - (gpu.memory_used or 0)),
                    "active_jobs": len(gpu_jobs),
                    "current_job": gpu_jobs[0].workload_type if gpu_jobs else None,
                    "agent_hostname": agent.hostname,
                    "is_available": gpu.is_available if gpu.is_available is not None else True
                })
                
                # Add connection between server and GPU
                connections.append({
                    "id": f"conn-{agent.hostname}-{gpu.id}",
                    "source": f"server-{agent.hostname}",
                    "target": str(gpu.id),
                    "type": "pcie"
                })

        # Create ethernet connections between control plane and other agents
        # This ensures all real agents (including the one designated as control plane, if it's not the hub) get connected.
        all_real_agents = [s for s in servers if not (isinstance(s, dict) and s.get("is_virtual"))]
        for agent_obj in all_real_agents:
            # Don't connect the hub to itself.
            if agent_obj.hostname != hub_hostname:
                connections.append({
                    "id": f"conn-control-{agent_obj.hostname}",
                    "source": f"server-{hub_hostname}",
                    "target": f"server-{agent_obj.hostname}",
                    "type": "ethernet"
                })

        logger.info(f"Topology: {len(final_servers)} servers, {len(gpus)} GPUs, {len(connections)} connections")

        return {
            "status": "success",
            "gpus": gpus,
            "servers": final_servers, 
            "connections": connections,
            "total_jobs": len(active_jobs),
            "total_gpus": len(gpus),
            "total_agents": len(final_servers), # Use servers count as it includes virtual node
            "control_plane": hub_hostname,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting topology: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )

@api_router.get("/debug/agents")
def debug_agents(db: Session = Depends(get_db)):
    """Debug endpoint to check registered agents"""
    try:
        agents = db.query(Agent).all()
        agent_info = []
        
        for agent in agents:
            gpus = db.query(GPU).filter_by(agent_id=agent.id).all()
            agent_info.append({
                "id": agent.id,
                "hostname": agent.hostname,
                "ip_address": agent.ip_address,
                "os": agent.os,
                "last_seen": agent.last_seen.isoformat() if agent.last_seen else None,
                "gpu_count": len(gpus),
                "gpus": [{"id": g.id, "name": g.name, "model": g.model, "status": g.status} for g in gpus]
            })
        
        return {
            "status": "success",
            "total_agents": len(agents),
            "agents": agent_info
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- Job Management Endpoints ---
@api_router.post("/jobs/submit")
def submit_job(job_request: JobRequest, db: Session = Depends(get_db)):
    """Submit a new job for GPU scheduling"""
    try:
        logger.info(f"Submitting job: {job_request.workload_type}")
        
        result = scheduler.schedule_job(
            workload_type=job_request.workload_type,
            command=job_request.command,
            preferred_gpu=job_request.preferred_gpu
        )
        
        if result.get("status") == "error":
            return JSONResponse(status_code=400, content=result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error submitting job: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})

@api_router.get("/jobs/{job_id}/status")
def get_job_status(job_id: int):
    """Get the current status of a job"""
    try:
        result = scheduler.get_job_status(job_id)
        
        if "error" in result and result.get("status") == "not_found":
            return JSONResponse(status_code=404, content=result)
        elif "error" in result:
            return JSONResponse(status_code=500, content=result)
            
        return result
        
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})

@api_router.get("/jobs")
def list_jobs():
    """List all jobs with their current status"""
    try:
        jobs = scheduler.list_jobs()
        return {
            "status": "success",
            "jobs": jobs,
            "count": len(jobs),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})

@api_router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: int):
    """Cancel a running job"""
    try:
        result = scheduler.cancel_job(job_id)
        
        if result.get("status") == "not_found":
            return JSONResponse(status_code=404, content=result)
        elif result.get("status") == "error":
            return JSONResponse(status_code=500, content=result)
            
        return result
        
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})

@api_router.get("/jobs/{job_id}/history")
def get_job_history(job_id: int, db: Session = Depends(get_db)):
    """Get the history/logs of a specific job"""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return JSONResponse(status_code=404, content={"status": "error", "error": "Job not found"})
        
        history = db.query(History).filter(History.job_id == job_id).order_by(History.timestamp.desc()).all()
        
        return {
            "status": "success",
            "job_id": job_id,
            "job_info": {
                "id": job.id,
                "workload_type": job.workload_type,
                "command": job.command,
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None
            },
            "history": [{
                "id": h.id,
                "action": h.action,
                "details": h.details,
                "timestamp": h.timestamp.isoformat() if h.timestamp else None
            } for h in history],
            "history_count": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting job history: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})

@api_router.post("/jobs/monitor")
def monitor_jobs_now():
    """Manually trigger job monitoring"""
    try:
        scheduler.monitor_jobs()
        return {
            "status": "success", 
            "message": "Job monitoring completed",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error monitoring jobs: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})

# --- System Status Endpoints ---
@api_router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    """Get overall system health and statistics"""
    try:
        total_agents = db.query(Agent).count()
        total_gpus = db.query(GPU).count()
        healthy_gpus = db.query(GPU).filter(GPU.status == "healthy").count()
        active_jobs = db.query(Job).filter(Job.status.in_(["running", "pending"])).count()
        completed_jobs = db.query(Job).filter(Job.status == "completed").count()
        
        return {
            "status": "success",
            "system_health": "healthy" if healthy_gpus > 0 else "warning",
            "statistics": {
                "total_agents": total_agents,
                "total_gpus": total_gpus,
                "healthy_gpus": healthy_gpus,
                "active_jobs": active_jobs,
                "completed_jobs": completed_jobs
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})

# --- UI Interaction Endpoints ---
# Dynamic hostname based on actual system
SELF_GPU_AGENT_HOSTNAME = f"{socket.gethostname()}-GPU-Detected"

@app.post("/gpu/detect", tags=["UI Interaction"])
def detect_self_gpu(db: Session = Depends(get_db)):
    """Detect GPUs on the control plane server - network binding independent"""
    try:
        logger.info("Starting GPU detection on control plane")
        detector = GPUDetector()
        report_data = detector.detect_gpus()

        if report_data['status'] == 'mock' or not report_data.get('gpus'):
            return JSONResponse(
                status_code=200,  # Changed from 404
                content={
                    "status": "no_gpus",
                    "message": "No GPUs detected on the server.",
                    "detection_method": report_data.get("detection_method", "unknown")
                }
            )

        # Create or update agent with dynamic hostname
        agent = db.query(Agent).filter_by(hostname=SELF_GPU_AGENT_HOSTNAME).first()
        if not agent:
            agent = Agent(
                hostname=SELF_GPU_AGENT_HOSTNAME,
                ip_address=get_local_ip(),  # Use actual control plane IP
                os="Control Plane Host",
                last_seen=datetime.now()
            )
            db.add(agent)
            db.flush()
        else:
            agent.last_seen = datetime.now()

        # Clear existing GPUs
        db.query(GPU).filter_by(agent_id=agent.id).delete()

        # Add detected GPUs
        gpus_added = 0
        for gpu_data in report_data["gpus"]:
            try:
                gpu = GPU(
                    id=gpu_data.get("id", f"GPU-{gpus_added}"),
                    name=gpu_data.get("name", f"GPU-{gpus_added}"),
                    model=gpu_data.get("model", "Unknown GPU"),
                    status=gpu_data.get("status", "healthy"),
                    temperature=gpu_data.get("temperature", 0),
                    utilization=gpu_data.get("utilization", 0),
                    memory_total=gpu_data.get("memoryTotal", 0),
                    memory_used=gpu_data.get("memoryUsed", 0),
                    agent_id=agent.id,
                    vram=gpu_data.get("memoryTotal", 0) // (1024**3) if gpu_data.get("memoryTotal") else 0,
                    is_available=gpu_data.get("status") == "healthy",
                    pci_bus_id=gpu_data.get("pci_bus_id", "")
                )
                db.add(gpu)
                gpus_added += 1
            except Exception as e:
                logger.error(f"Error adding detected GPU: {e}")
                continue
        
        db.commit()
        logger.info(f"Successfully detected and added {gpus_added} GPUs")

        return {
            "status": "success",
            "gpus": report_data["gpus"],
            "detection_method": report_data["detection_method"],
            "message": f"Detected {len(report_data['gpus'])} GPU(s) on the server.",
            "gpus_added": gpus_added
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"GPU detection error: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500, 
            content={"status": "error", "message": str(e)}
        )

@app.get("/gpu/self", tags=["UI Interaction"])
def get_self_gpu(db: Session = Depends(get_db)):
    """Get GPUs detected on the control plane server"""
    try:
        agent = db.query(Agent).filter_by(hostname=SELF_GPU_AGENT_HOSTNAME).first()
        
        if not agent:
            return {
                "status": "no_agent",
                "gpu": None,
                "message": "No self-detected GPUs found. Run detection first."
            }
        
        gpus = db.query(GPU).filter_by(agent_id=agent.id).all()
        
        if not gpus:
            return {
                "status": "no_gpus",
                "gpu": None,
                "message": "No GPUs found for this agent."
            }
        
        # Return GPU data
        gpu_data = []
        for gpu in gpus:
            gpu_dict = {c.name: getattr(gpu, c.name) for c in gpu.__table__.columns}
            gpu_data.append(gpu_dict)
        
        return {
            "status": "success",
            "gpu": gpu_data[0] if gpu_data else None,
            "gpus": gpu_data,
            "count": len(gpu_data)
        }
        
    except Exception as e:
        logger.error(f"Error getting self GPU: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )

# --- Register Routers ---
app.include_router(agent_router)
app.include_router(api_router)

# --- Health Check ---
@app.get("/health")
def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "service": "GPU Nebula Control Plane",
        "version": "2.1.0",
        "timestamp": datetime.now().isoformat()
    }

# --- Main Entry Point ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting GPU Nebula Control Plane...")
    # Bind to the specific IP address
    uvicorn.run(
        app, 
        host="0.0.0.0",
        port=8080, 
        reload=False,
        log_level="info"
    )
