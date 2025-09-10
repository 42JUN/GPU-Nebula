import subprocess
import json
import psutil
from typing import List, Dict, Optional
from datetime import datetime

from ..models.gpu import GPUBase, GPUMetrics

def _run_nvidia_smi(query: str) -> Optional[List[str]]:
    """Runs nvidia-smi command and returns parsed JSON output."""
    try:
        command = [
            "nvidia-smi",
            "--query-gpu=" + query,
            "--format=csv,noheader,nounits"
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        # Assuming a single GPU for now, or multiple GPUs with consistent output order
        # For multiple GPUs, this parsing needs to be more robust
        # For simplicity, let's assume query returns one line per GPU
        
        # Example query: "uuid,name,driver_version,cuda_version,memory.total"
        # Example output: "GPU-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx,NVIDIA GeForce RTX 3080,535.113.01,12.2,10240 MiB"
        
        # This parsing is very basic and needs improvement for complex queries
        # A better approach would be to use nvidia-ml-py3 directly.
        
        # For now, let's return raw lines and parse them in the calling function
        return lines
    except FileNotFoundError:
        print("nvidia-smi not found. Please ensure NVIDIA drivers are installed.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error running nvidia-smi: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def get_gpu_details() -> List[GPUBase]:
    """Discovers NVIDIA GPUs and returns their static details."""
    gpus_data = []
    query = "uuid,name,driver_version,cuda_version,gpu_bus_id,memory.total"
    raw_data = _run_nvidia_smi(query)

    if raw_data:
        for line in raw_data:
            parts = line.split(',')
            if len(parts) == 6:
                uuid, name, driver_version, cuda_version, serial, memory_total_mib = [p.strip() for p in parts]
                # For simplicity, using bus_id as serial for now, needs proper serial from nvidia-smi
                # nvidia-smi --query-gpu=gpu_name,gpu_uuid,driver_version,cuda_version,serial --format=csv
                
                # Placeholder for model and vendor, as nvidia-smi doesn't directly provide them in this query
                # You might need to map based on name or use nvidia-ml-py3
                model = name # Using name as model for now
                vendor = "NVIDIA"

                gpus_data.append(GPUBase(
                    uuid=uuid,
                    name=name,
                    vendor=vendor,
                    model=model,
                    serial=serial, # Using bus_id as serial for now
                    driver_version=driver_version,
                    cuda_version=cuda_version,
                    compute_capability=None, # Not directly available from this query
                    memory_total_mb=int(memory_total_mib.replace(' MiB', '')) if 'MiB' in memory_total_mib else None
                ))
    return gpus_data

def get_gpu_metrics(gpu_uuid: str) -> Optional[GPUMetrics]:
    """Collects real-time metrics for a specific GPU."""
    query = "utilization.gpu,utilization.memory,temperature.gpu,power.draw,fan.speed,memory.used,memory.total"
    raw_data = _run_nvidia_smi(query)

    if raw_data:
        # Assuming the first line corresponds to the GPU we are looking for,
        # which is not robust for multiple GPUs.
        # A better approach would be to query by UUID or use nvidia-ml-py3.
        # For now, we'll just take the first GPU's metrics.
        line = raw_data[0] 
        parts = line.split(',')
        if len(parts) == 7:
            util_gpu, util_mem, temp_gpu, power_draw, fan_speed, mem_used, mem_total = [p.strip() for p in parts]
            
            return GPUMetrics(
                timestamp=datetime.now(),
                utilization_gpu=float(util_gpu.replace('%', '')) if '%' in util_gpu else None,
                utilization_memory=float(util_mem.replace('%', '')) if '%' in util_mem else None,
                temperature_gpu=float(temp_gpu) if temp_gpu.replace('.', '').isdigit() else None,
                power_draw=float(power_draw.replace(' W', '')) if 'W' in power_draw else None,
                fan_speed=float(fan_speed.replace('%', '')) if '%' in fan_speed else None,
                memory_used=float(mem_used.replace(' MiB', '')) if 'MiB' in mem_used else None,
                memory_total=float(mem_total.replace(' MiB', '')) if 'MiB' in mem_total else None
            )
    return None

# Example of getting CPU/Memory usage of the system (using psutil)
def get_system_metrics():
    """Collects system-wide CPU and memory metrics."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory_info.percent,
        "memory_used_gb": memory_info.used / (1024**3),
        "memory_total_gb": memory_info.total / (1024**3),
    }
