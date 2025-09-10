import socket
import platform
import requests
import subprocess

# Point this to your backend (change IP if running on LAN server)
BACKEND_URL = "http://localhost:8080/api/v1/agent/report-in"

def detect_gpus():
    gpus = []
    try:
        # Try NVIDIA GPUs via nvidia-smi
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,temperature.gpu,utilization.gpu,memory.total", "--format=csv,noheader,nounits"],
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
    except FileNotFoundError:
        print("⚠️ nvidia-smi not found. No NVIDIA GPU detected.")

    if not gpus:
        # fallback: CPU-only
        gpus.append({
            "id": "gpu-0",
            "name": "CPU",
            "model": "CPU-only",
            "status": "idle",
            "temperature": 0,
            "utilization": 0,
            "memoryTotal": 0
        })

    return gpus

def report_to_backend():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    os_info = platform.platform()

    payload = {
        "agent_info": {
            "hostname": hostname,
            "ip_address": ip,
            "os": os_info
        },
        "gpu_report": {
            "gpus": detect_gpus(),
            "servers": [],          # not needed yet
            "connections": [],      # not needed yet
            "detection_method": "nvidia-smi",
            "status": "success"
        }
    }

    try:
        res = requests.post(BACKEND_URL, json=payload)
        print("✅ Report sent:", res.json())
    except Exception as e:
        print("❌ Failed to report:", e)

if __name__ == "__main__":
    report_to_backend()
