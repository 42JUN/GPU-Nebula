from pydantic import BaseModel
from typing import List, Optional

class NetworkBase(BaseModel):
    name: str
    description: Optional[str] = None

class NetworkCreate(NetworkBase):
    gpu_uuids: List[str] = [] # List of GPU UUIDs belonging to this network

class NetworkDb(NetworkBase):
    id: int

    class Config:
        orm_mode = True

class Network(NetworkDb):
    # This model might include relationships to GPUs later
    pass
