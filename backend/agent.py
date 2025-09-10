import socket
import platform
import requests
import subprocess
import time
import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Configuration - CHANGE THIS TO YOUR DELL G15 IP
CONTROL_PLANE_URL = "http://192.168.1.31:8080"  # Replace XXX with Dell G15 IP
AGENT_PORT = 8001
REPORT_INTERVAL = 15  # seconds

app = FastAPI(title="GPU Nebula Agent", version="1.0.0")

class JobRequest(BaseModel):
    job_id: int
    command: str
    gpu_id: str
    workload_type: str

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def detect_gpus():
    """Detect GPUs - Mac will return CPU-only"""
    gpus = []
    
    # Try NVIDIA first
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,temperature.gpu,utilization.gpu,memory.total", 
             "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                idx, name, temp, util, mem = [x.strip() for x in line.split(",")]
                gpus.append({
                    "id": f"gpu-{idx}",
                    "name": name,
                    "model": name,
                    "status": "active" if int(util) > 0 else "idle",
                    "temperature": int(temp),
                    "utilization": int(util),
                    "memoryTotal": int(mem) * 1024 * 1024  # MB → bytes
                })
        print("✅ NVIDIA GPUs detected")
    except FileNotFoundError:
        print("ℹ️ nvidia-smi not found")
    
    # Try macOS GPU detection
    if platform.system() == "Darwin" and not gpus:
        try:
            # Try to get Metal GPU info on Mac
            result = subprocess.run(["system_profiler", "SPDisplaysDataType", "-json"], 
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                displays = data.get("SPDisplaysDataType", [])
                for display in displays:
                    if "sppci_model" in display:
                        gpus.append({
                            "id": "gpu-0",
                            "name": display.get("sppci_model", "Mac GPU"),
                            "model": "Mac GPU",
                            "status": "idle",
                            "temperature": 0,
                            "utilization": 0,
                            "memoryTotal": 0
                        })
                        print("✅ Mac GPU detected")
                        break
        except:
            print("⚠️ Could not detect Mac GPU")
    
    # Fallback: CPU-only agent
    if not gpus:
        gpus.append({
            "id": "cpu-0",
            "name": f"CPU Agent ({platform.processor() or 'CPU'})",
            "model": "CPU-only",
            "status": "idle",
            "temperature": 0,
            "utilization": 0,
            "memoryTotal": 0
        })
        print("ℹ️ Running as CPU-only agent")
    
    return gpus

@app.post("/agent/run-job")
async def run_job(job_request: JobRequest):
    """Execute a job on this agent"""
    try:
        print(f"🚀 Received job {job_request.job_id}: {job_request.command}")
        
        # Launch the job
        process = subprocess.Popen(
            job_request.command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        return {
            "status": "started",
            "pid": process.pid,
            "message": f"Job {job_request.job_id} started on {socket.gethostname()}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agent/status")
async def get_status():
    """Get agent status"""
    return {
        "hostname": socket.gethostname(),
        "status": "healthy",
        "gpu_count": len(detect_gpus()),
        "last_update": time.time(),
        "platform": platform.system(),
        "ip": get_local_ip()
    }

def report_to_backend():
    """Report this agent's status to control plane"""
    while True:
        try:
            hostname = socket.gethostname()
            
            payload = {
                "agent_info": {
                    "hostname": hostname,
                    "ip_address": get_local_ip(),
                    "os": f"{platform.system()} {platform.release()}"
                },
                "gpu_report": {
                    "gpus": detect_gpus(),
                    "servers": [],
                    "connections": [],
                    "detection_method": "multi-platform",
                    "status": "success"
                }
            }
            
            print(f"📡 Reporting to control plane: {CONTROL_PLANE_URL}/api/v1/agent/report-in")
            response = requests.post(
                f"{CONTROL_PLANE_URL}/api/v1/agent/report-in",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Successfully reported to control plane ({hostname})")
            else:
                print(f"❌ Failed to report: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"🔌 Cannot connect to control plane at {CONTROL_PLANE_URL}")
        except Exception as e:
            print(f"❌ Error reporting to control plane: {e}")
        
        time.sleep(REPORT_INTERVAL)

if __name__ == "__main__":
    hostname = socket.gethostname()
    ip = get_local_ip()
    
    print(f"🤖 Starting GPU Nebula Agent")
    print(f"🏷️ Hostname: {hostname}")
    print(f"🌐 IP Address: {ip}")
    print(f"💻 Platform: {platform.system()}")
    print(f"📡 Control Plane: {CONTROL_PLANE_URL}")
    print(f"🔧 GPUs Found: {len(detect_gpus())}")
    
    # Start background reporting thread
    reporting_thread = threading.Thread(target=report_to_backend, daemon=True)
    reporting_thread.start()
    
    # Start the FastAPI server
    print(f"🚀 Starting agent server on {ip}:{AGENT_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
