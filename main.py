from typing import Union 
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback

# Setup FastAPI app
app = FastAPI(title="GPU Nebula Backend", version="1.0.0", description="Advanced GPU Cluster Management API")

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Try NVML init
try:
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
    print("✅ NVML Successfully Initialized - Real GPU Detection Enabled")
except Exception as e:
    NVML_AVAILABLE = False
    print(f"⚠️ NVML Not Available - Using Mock Data: {e}")


def get_gpu_name_safe(handle):
    """Safely get GPU name handling both string and bytes returns"""
    try:
        name = pynvml.nvmlDeviceGetName(handle)
        # If it's bytes, decode it. If it's already a string, return as-is
        if isinstance(name, bytes):
            return name.decode('utf-8')
        return str(name)
    except Exception as e:
        print(f"Error getting GPU name: {e}")
        return "Unknown GPU"

def get_topology():
    """Get GPU topology with real hardware detection or mock data"""
    try:
        if NVML_AVAILABLE:
            print("🔍 Detecting Real GPU Hardware...")
            
            gpu_nodes = []
            gpu_links = []
            servers = []
            connections = []
            
            # Get real GPU count
            gpu_count = pynvml.nvmlDeviceGetCount()
            print(f"📊 Found {gpu_count} GPU(s)")
            
            # Real GPU Detection 
            for i in range(gpu_count):
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    gpu_name = get_gpu_name_safe(handle)
                    
                    # Get additional GPU info
                    try:
                        memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                        power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert to watts
                        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    except:
                        # Fallback values if we can't get detailed info
                        memory_info = type('obj', (object,), {'total': 24000000000, 'used': 8000000000})()
                        temp = 65
                        power = 250.0
                        utilization = type('obj', (object,), {'gpu': 75, 'memory': 60})()
                    
                    gpu_nodes.append({
                        "id": f"gpu-{i}",
                        "name": f"GPU-{i}",
                        "model": gpu_name,
                        "type": "gpu",
                        "status": "healthy",
                        "temperature": temp,
                        "powerUsage": power,
                        "memoryUsed": memory_info.used,
                        "memoryTotal": memory_info.total,
                        "utilization": utilization.gpu,
                        "memoryUtilization": utilization.memory
                    })
                    
                except Exception as e:
                    print(f"Error processing GPU {i}: {e}")
                    # Add fallback GPU data
                    gpu_nodes.append({
                        "id": f"gpu-{i}",
                        "name": f"GPU-{i}",
                        "model": "Unknown GPU",
                        "type": "gpu",
                        "status": "warning",
                        "temperature": 65,
                        "powerUsage": 250.0,
                        "memoryUsed": 8000000000,
                        "memoryTotal": 24000000000,
                        "utilization": 50,
                        "memoryUtilization": 40
                    })
            
            # Check GPU-to-GPU connectivity
            for i in range(gpu_count):
                for j in range(i + 1, gpu_count):
                    try:
                        handle_i = pynvml.nvmlDeviceGetHandleByIndex(i)
                        handle_j = pynvml.nvmlDeviceGetHandleByIndex(j)
                        
                        # Check P2P capability
                        p2p_status = pynvml.nvmlDeviceGetP2PStatus(
                            handle_i, handle_j, pynvml.NVML_P2P_CAPS_INDEX_READ
                        )
                        
                        if p2p_status == pynvml.NVML_P2P_STATUS_OK:
                            connections.append({
                                "id": f"conn-{i}-{j}",
                                "source": f"gpu-{i}",
                                "target": f"gpu-{j}",
                                "type": "nvlink",
                                "bandwidth": "600 GB/s",
                                "status": "active"
                            })
                    except Exception as e:
                        print(f"Error checking P2P between GPU {i} and {j}: {e}")
            
            # Add server node (representing the host system)
            servers.append({
                "id": "server-0",
                "name": "Server-1",
                "type": "server",
                "cpu": "Intel Xeon",
                "status": "healthy",
                "uptime": "99.9%"
            })
            
            # Connect GPUs to server
            for i in range(gpu_count):
                connections.append({
                    "id": f"conn-server-gpu-{i}",
                    "source": "server-0",
                    "target": f"gpu-{i}",
                    "type": "pcie",
                    "bandwidth": "32 GB/s",
                    "status": "active"
                })
            
            print(f"✅ Successfully created topology: {len(gpu_nodes)} GPUs, {len(servers)} servers, {len(connections)} connections")
            
            return {
                "gpus": gpu_nodes,
                "servers": servers,
                "connections": connections,
                "timestamp": "2024-08-27T19:13:11Z",
                "status": "success"
            }
            
        else:
            print("🎭 Using Mock Data (NVML Not Available)")
            # Enhanced mock data for testing
            return {
                "gpus": [
                    {
                        "id": "gpu-0",
                        "name": "GPU-0",
                        "model": "NVIDIA RTX 4090",
                        "type": "gpu",
                        "status": "healthy",
                        "temperature": 68,
                        "powerUsage": 420.5,
                        "memoryUsed": 12000000000,
                        "memoryTotal": 24000000000,
                        "utilization": 85,
                        "memoryUtilization": 70
                    },
                    {
                        "id": "gpu-1", 
                        "name": "GPU-1",
                        "model": "NVIDIA RTX 4090",
                        "type": "gpu",
                        "status": "healthy",
                        "temperature": 72,
                        "powerUsage": 398.2,
                        "memoryUsed": 18000000000,
                        "memoryTotal": 24000000000,
                        "utilization": 92,
                        "memoryUtilization": 85
                    },
                    {
                        "id": "gpu-2",
                        "name": "GPU-2", 
                        "model": "NVIDIA RTX 4080",
                        "type": "gpu",
                        "status": "warning",
                        "temperature": 78,
                        "powerUsage": 315.8,
                        "memoryUsed": 14000000000,
                        "memoryTotal": 16000000000,
                        "utilization": 78,
                        "memoryUtilization": 88
                    },
                    {
                        "id": "gpu-3",
                        "name": "GPU-3",
                        "model": "NVIDIA RTX 4080", 
                        "type": "gpu",
                        "status": "healthy",
                        "temperature": 71,
                        "powerUsage": 289.4,
                        "memoryUsed": 8000000000,
                        "memoryTotal": 16000000000,
                        "utilization": 65,
                        "memoryUtilization": 55
                    }
                ],
                "servers": [
                    {
                        "id": "server-0",
                        "name": "Server-1",
                        "type": "server", 
                        "cpu": "Intel Xeon E5-2698 v4",
                        "status": "healthy",
                        "uptime": "99.97%"
                    },
                    {
                        "id": "server-1",
                        "name": "Server-2",
                        "type": "server",
                        "cpu": "AMD EPYC 7542",
                        "status": "healthy", 
                        "uptime": "99.85%"
                    }
                ],
                "connections": [
                    {
                        "id": "conn-0-1",
                        "source": "gpu-0",
                        "target": "gpu-1", 
                        "type": "nvlink",
                        "bandwidth": "600 GB/s",
                        "status": "active"
                    },
                    {
                        "id": "conn-1-2",
                        "source": "gpu-1",
                        "target": "gpu-2",
                        "type": "nvlink", 
                        "bandwidth": "600 GB/s",
                        "status": "active"
                    },
                    {
                        "id": "conn-2-3",
                        "source": "gpu-2",
                        "target": "gpu-3",
                        "type": "pcie",
                        "bandwidth": "32 GB/s",
                        "status": "active"
                    },
                    {
                        "id": "conn-server-gpu-0",
                        "source": "server-0",
                        "target": "gpu-0",
                        "type": "pcie",
                        "bandwidth": "32 GB/s", 
                        "status": "active"
                    },
                    {
                        "id": "conn-server-gpu-1", 
                        "source": "server-0",
                        "target": "gpu-1",
                        "type": "pcie",
                        "bandwidth": "32 GB/s",
                        "status": "active"
                    },
                    {
                        "id": "conn-server2-gpu-2",
                        "source": "server-1", 
                        "target": "gpu-2",
                        "type": "pcie",
                        "bandwidth": "32 GB/s",
                        "status": "active"
                    },
                    {
                        "id": "conn-server2-gpu-3",
                        "source": "server-1",
                        "target": "gpu-3", 
                        "type": "pcie",
                        "bandwidth": "32 GB/s",
                        "status": "active"
                    }
                ],
                "timestamp": "2024-08-27T19:13:11Z",
                "status": "mock"
            }
            
    except Exception as e:
        print(f"❌ Error in get_topology: {e}")
        traceback.print_exc()
        return {
            "gpus": [],
            "servers": [],
            "connections": [],
            "timestamp": "2024-08-27T19:13:11Z",
            "status": "error",
            "error": str(e)
        }
    


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "🚀 GPU Nebula Backend API",
        "version": "1.0.0",
        "status": "online",
        "nvml_available": NVML_AVAILABLE,
        "endpoints": {
            "topology": "/topology",
            "docs": "/docs"
        }
    }

@app.get("/topology")
async def topology():
    """Get GPU cluster topology data"""
    try:
        data = get_topology()
        print(f"📤 Sending topology data: {len(data.get('gpus', []))} GPUs, {len(data.get('servers', []))} servers")
        return JSONResponse(content=data)
    except Exception as e:
        print(f"❌ Error in topology endpoint: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(e),
                "status": "error"
            }
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2024-08-27T19:13:11Z",
        "nvml_available": NVML_AVAILABLE
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting GPU Nebula Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
