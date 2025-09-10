from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class WorkloadBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "pending" # pending, running, completed, failed
    priority: int = 0 # Higher number means higher priority
    resource_requirements: Dict[str, float] = {} # e.g., {"gpu_memory_gb": 16, "gpu_count": 1}
    # Add more fields for workload classification (e.g., communication patterns)

class WorkloadCreate(WorkloadBase):
    pass

class WorkloadDb(WorkloadBase):
    id: int
    submitted_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_gpu_uuid: Optional[str] = None # The GPU where the workload is running

    class Config:
        orm_mode = True

class Workload(WorkloadDb):
    pass
