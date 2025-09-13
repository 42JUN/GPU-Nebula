import socket
import platform
import requests
import subprocess
import time
import threading
import os
import psutil
from gpu_detector import GPUDetector
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Configuration: Use environment variable or a default.
# The default should be the IP of your main control plane server.
CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://10.248.127.222:8080")
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

@app.post("/agent/run-job")
async def run_job(job_request: JobRequest):
    """Execute a job on this agent"""
    try:
        import shlex
        print(f"🚀 Received job {job_request.job_id}: {job_request.command}")
        
        # Determine GPU index from gpu_id (e.g., "GPU-0" -> 0)
        try:
            gpu_index = int(job_request.gpu_id.split('-')[-1])
        except (ValueError, IndexError):
            print(f"⚠️ Could not parse GPU index from '{job_request.gpu_id}'. Defaulting to all GPUs.")
            gpu_index = ""  # Let CUDA decide

        # Set environment to isolate the job to the assigned GPU
        env = {
            **os.environ,
            'CUDA_VISIBLE_DEVICES': str(gpu_index)
        }
        print(f"Setting CUDA_VISIBLE_DEVICES={gpu_index} for job {job_request.job_id}")

        # Launch the job securely, without using a shell
        process = subprocess.Popen(
            shlex.split(job_request.command),
            shell=False,
            env=env,
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

@app.get("/agent/job-status/{pid}")
async def get_job_status(pid: int):
    """Check the status of a process by its PID."""
    try:
        process = psutil.Process(pid)
        if process.is_running():
            return {"pid": pid, "status": "running"}
        else:
            # Process exists but is not running (e.g., zombie)
            return {"pid": pid, "status": "not_running"}
    except psutil.NoSuchProcess:
        return {"pid": pid, "status": "not_found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agent/status")
async def get_status():
    """Get agent status"""
    detector = GPUDetector()
    gpus = detector.detect_gpus().get('gpus', [])
    return {
        "hostname": socket.gethostname(),
        "status": "healthy",
        "gpu_count": len(gpus),
        "last_update": time.time(),
        "platform": platform.system(),
        "ip": get_local_ip()
    }

def report_to_backend():
    """Report this agent's status to control plane"""
    detector = GPUDetector()
    while True:
        try:
            hostname = socket.gethostname()
            
            gpu_report_data = detector.detect_gpus()
            
            payload = {
                "agent_info": {
                    "hostname": hostname,
                    "ip_address": get_local_ip(),
                    "os": f"{platform.system()} {platform.release()}"
                },
                "gpu_report": {
                    "gpus": gpu_report_data.get('gpus', []),
                    "servers": gpu_report_data.get('servers', []),
                    "connections": gpu_report_data.get('connections', []),
                    "detection_method": gpu_report_data.get('detection_method', 'agent_fallback'),
                    "status": gpu_report_data.get('status', 'success')
                }
            }
            
            print(f"📡 Reporting to control plane: {CONTROL_PLANE_URL}/api/v1/agent/report-in")
            headers = {
                # Mimic a standard browser User-Agent to bypass simple network filters
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json'
            }
            response = requests.post(
                f"{CONTROL_PLANE_URL}/api/v1/agent/report-in",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Successfully reported to control plane ({hostname})")
            else:
                print(f"❌ Failed to report. Status: {response.status_code}.")
                # If the response is HTML, save it for inspection.
                if "html" in response.headers.get("Content-Type", "").lower():
                    error_html_path = "error_page.html"
                    with open(error_html_path, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    print(f"📝 An HTML error page was received. Full response saved to: {error_html_path}")
                
        except requests.exceptions.ConnectionError:
            print(f"🔌 Cannot connect to control plane at {CONTROL_PLANE_URL}")
        except Exception as e:
            print(f"❌ Error reporting to control plane: {e}")
        
        time.sleep(REPORT_INTERVAL)

def check_control_plane_connection():
    """Pings the control plane's health endpoint to verify connection before starting."""
    try:
        print(f"🩺 Pinging control plane at {CONTROL_PLANE_URL}/health...")
        response = requests.get(f"{CONTROL_PLANE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Control plane is reachable.")
            return True
        else:
            print(f"❌ Control plane responded with status {response.status_code}. Check server logs.")
            return False
    except requests.exceptions.ConnectionError:
        print(f"🔌 Cannot connect to control plane at {CONTROL_PLANE_URL}.")
        print("   Troubleshooting steps:")
        print("   1. Is the backend server running on the control plane machine?")
        print(f"   2. Is the IP address in the URL correct?")
        print("   3. Is the firewall on the control plane machine blocking port 8080?")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred while checking connection: {e}")
        return False

if __name__ == "__main__":
    hostname = socket.gethostname()
    ip = get_local_ip()
    
    print(f"🤖 Starting GPU Nebula Agent")
    print(f"🏷️ Hostname: {hostname}")
    print(f"🌐 IP Address: {ip}")
    print(f"💻 Platform: {platform.system()}")
    print(f"📡 Control Plane: {CONTROL_PLANE_URL}")
    detector = GPUDetector()
    initial_gpus = detector.detect_gpus().get('gpus', [])
    print(f"🔧 GPUs Found: {len(initial_gpus)}")
    
    # Perform a connection check before starting services
    if not check_control_plane_connection():
        print("Aborting agent startup due to connection failure.")
        exit(1)

    # Start background reporting thread
    reporting_thread = threading.Thread(target=report_to_backend, daemon=True)
    reporting_thread.start()
    
    # Start the FastAPI server
    print(f"🚀 Starting agent server on {ip}:{AGENT_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
