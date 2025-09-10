from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class Interconnect(BaseModel):
    type: str # e.g., "NVLink", "PCIe", "InfiniBand"
    bandwidth_gbps: Optional[float] = None
    latency_ms: Optional[float] = None

class TopologyNode(BaseModel):
    gpu_uuid: str
    # Add other node-specific properties if needed, e.g., host_id, rack_id

class TopologyEdge(BaseModel):
    source_gpu_uuid: str
    target_gpu_uuid: str
    interconnect: Interconnect

class Topology(BaseModel):
    nodes: List[TopologyNode] = []
    edges: List[TopologyEdge] = []
    last_updated: datetime
