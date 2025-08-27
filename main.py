from typing import Union 
from fastapi import FastAPI
from fastapi.responses import JSONResponse

## setup FastAPI app



# Try NVML init
try:
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
except:
    NVML_AVAILABLE = False


app = FastAPI(title="GPU Backend", version="1.0.0")


## gpu 1.Topology endpoint 


def get_topology():
 gpu_nodes = []
 gpu_links = []
 if NVML_AVAILABLE:
    
    no_of_gpu_device = pynvml.nvmlDeviceGetCount()

    
    
        # Real GPU Detection 
    for i in range(no_of_gpu_device):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        gpu_nodes.append({
            "id": f"GPU-{i}",
            "name": pynvml.nvmlDeviceGetName(handle).decode()
        })


        # Check connectivity between GPU i and all others (j)
        for j in range(i + 1, no_of_gpu_device):
            peer_status = pynvml.nvmlDeviceGetP2PStatus(
                handle,
                pynvml.nvmlDeviceGetHandleByIndex(j),
                pynvml.NVML_P2P_CAPS_INDEX_NVLINK
            )
            if peer_status == pynvml.NVML_SUCCESS:
                gpu_links.append({
                    "source": f"GPU-{i}",
                    "target": f"GPU-{j}",
                    "connection": "NVLINK"
                })


    return {"topology": {"nodes": gpu_nodes, "links": gpu_links}}
   
 else:
          #fake testing data 
        gpu_nodes = [
            {"id": "GPU-0", "name": "Fake NVIDIA A100", "pci_bus": "0000:00:01.0"},
            {"id": "GPU-1", "name": "Fake NVIDIA A100", "pci_bus": "0000:00:02.0"},
            {"id": "GPU-2", "name": "Fake NVIDIA V100", "pci_bus": "0000:00:03.0"}
        ]
        gpu_links = [
            {"source": "GPU-0", "target": "GPU-1", "connection": "NVLink"},
            {"source": "GPU-1", "target": "GPU-2", "connection": "PCIe"}
        ]
        return {"topology": {"nodes": gpu_nodes, "links": gpu_links}}
    


@app.get("/topology")
async def topology():
    return JSONResponse(content={"topology": get_topology()})

'''
@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
'''
