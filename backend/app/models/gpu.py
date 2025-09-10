from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class GPUMetrics(BaseModel):
    timestamp: datetime
    utilization_gpu: Optional[float] = None  # Percentage
    utilization_memory: Optional[float] = None # Percentage
    temperature_gpu: Optional[float] = None   # Celsius
    power_draw: Optional[float] = None        # Watts
    fan_speed: Optional[float] = None         # Percentage
    memory_used: Optional[float] = None       # MB
    memory_total: Optional[float] = None      # MB

class GPUBase(BaseModel):
    uuid: str
    name: str
    vendor: str
    model: str
    serial: str
    driver_version: str
    cuda_version: Optional[str] = None
    compute_capability: Optional[str] = None
    memory_total_mb: Optional[int] = None
    # Add more properties as needed

class GPUCreate(GPUBase):
    pass

class GPUDb(GPUBase):
    id: int
    registered_at: datetime

    class Config:
        orm_mode = True

class GPU(GPUDb):
    metrics: Optional[List[GPUMetrics]] = [] # Real-time metrics
    # Add relationships to other models later (e.g., topology, workloads)
