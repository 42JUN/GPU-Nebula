from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB # For resource_requirements

from ..database import Base

class SQLWorkload(Base):
    __tablename__ = "workloads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String, nullable=True)
    status = Column(String, default="pending")
    priority = Column(Integer, default=0)
    resource_requirements = Column(JSONB) # Store as JSONB for flexibility
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    assigned_gpu_uuid = Column(String, nullable=True) # UUID of the GPU where it's assigned

    # Potentially add relationship to GPU if we want to link directly to the SQLGPU object
    # assigned_gpu_id = Column(Integer, ForeignKey("gpus.id"), nullable=True)
    # assigned_gpu = relationship("SQLGPU")
