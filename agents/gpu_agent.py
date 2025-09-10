import time
import requests
import json
from datetime import datetime
from typing import Dict, Any

# Assuming the backend is accessible at this URL
# In a real deployment, this would be configurable
BACKEND_URL = "http://localhost:8000" # Or the Docker service name if agents are in the same Docker network

def register_agent(gpu_details: Dict[str, Any]) -> Dict[str, Any]:
    """Registers the GPU agent with the central control plane."""
    try:
        response = requests.post(f"{BACKEND_URL}/api/agents/register", json=gpu_details)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error registering agent: {e}")
        return {"error": str(e)}

def send_gpu_metrics(gpu_id: int, metrics: Dict[str, Any]):
    """Sends GPU metrics to the central control plane."""
    try:
        response = requests.post(f"{BACKEND_URL}/api/gpus/{gpu_id}/metrics", json=metrics)
        response.raise_for_status()
        # print(f"Metrics sent for GPU {gpu_id}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending metrics for GPU {gpu_id}: {e}")

def main():
    # Placeholder for actual GPU discovery
    # In a real scenario, this would use backend/app/services/gpu_discovery.py
    # For now, let's mock some GPU details
    mock_gpu_details = {
        "uuid": "GPU-MOCK-1234-5678-90AB-CDEF",
        "name": "Mock GPU",
        "vendor": "MockCorp",
        "model": "MockModel",
        "serial": "MOCKSERIAL123",
        "driver_version": "1.0.0",
        "cuda_version": "11.0",
        "compute_capability": "8.0",
        "memory_total_mb": 8192
    }

    registered_gpu = register_agent(mock_gpu_details)
    if "error" in registered_gpu:
        print("Agent registration failed. Exiting.")
        return

    gpu_id = registered_gpu.get("id")
    if not gpu_id:
        print("Could not get GPU ID after registration. Exiting.")
        return

    print(f"Agent registered with GPU ID: {gpu_id}")

    while True:
        # Collect mock metrics
        mock_metrics = {
            "timestamp": datetime.now().isoformat(),
            "utilization_gpu": 50.0,
            "utilization_memory": 30.0,
            "temperature_gpu": 60.0,
            "power_draw": 150.0,
            "fan_speed": 40.0,
            "memory_used": 2048.0,
            "memory_total": 8192.0
        }
        send_gpu_metrics(gpu_id, mock_metrics)
        time.sleep(5) # Send metrics every 5 seconds

if __name__ == "__main__":
    main()
