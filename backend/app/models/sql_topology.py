from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB # For interconnect details

from ..database import Base

class SQLInterconnect(Base):
    __tablename__ = "interconnects"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String) # e.g., "NVLink", "PCIe", "InfiniBand"
    bandwidth_gbps = Column(Float, nullable=True)
    latency_ms = Column(Float, nullable=True)

class SQLTopologyNode(Base):
    __tablename__ = "topology_nodes"

    id = Column(Integer, primary_key=True, index=True)
    gpu_uuid = Column(String, unique=True, index=True)
    # Add other node-specific properties if needed, e.g., host_id, rack_id

class SQLTopologyEdge(Base):
    __tablename__ = "topology_edges"

    id = Column(Integer, primary_key=True, index=True)
    source_gpu_uuid = Column(String, ForeignKey("topology_nodes.gpu_uuid"))
    target_gpu_uuid = Column(String, ForeignKey("topology_nodes.gpu_uuid"))
    interconnect_id = Column(Integer, ForeignKey("interconnects.id"))
    last_updated = Column(DateTime(timezone=True), server_default=func.now())

    source_node = relationship("SQLTopologyNode", foreign_keys=[source_gpu_uuid])
    target_node = relationship("SQLTopologyNode", foreign_keys=[target_gpu_uuid])
    interconnect = relationship("SQLInterconnect")
