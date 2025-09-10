from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base
from .sql_network import network_gpus # Import the association table

class SQLGPUMetrics(Base):
    __tablename__ = "gpu_metrics"

    id = Column(Integer, primary_key=True, index=True)
    gpu_id = Column(Integer, ForeignKey("gpus.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    utilization_gpu = Column(Float)
    utilization_memory = Column(Float)
    temperature_gpu = Column(Float)
    power_draw = Column(Float)
    fan_speed = Column(Float)
    memory_used = Column(Float)
    memory_total = Column(Float)

    gpu = relationship("SQLGPU", back_populates="metrics")

class SQLGPU(Base):
    __tablename__ = "gpus"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, index=True)
    name = Column(String)
    vendor = Column(String)
    model = Column(String)
    serial = Column(String)
    driver_version = Column(String)
    cuda_version = Column(String, nullable=True)
    compute_capability = Column(String, nullable=True)
    memory_total_mb = Column(Integer, nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())

    metrics = relationship("SQLGPUMetrics", back_populates="gpu")
    networks = relationship("SQLNetwork", secondary=network_gpus, back_populates="gpus")
