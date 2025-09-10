from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from ..database import Base

# Association table for many-to-many relationship between networks and GPUs
network_gpus = Table(
    "network_gpus",
    Base.metadata,
    Column("network_id", Integer, ForeignKey("networks.id"), primary_key=True),
    Column("gpu_id", Integer, ForeignKey("gpus.id"), primary_key=True),
)

class SQLNetwork(Base):
    __tablename__ = "networks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)

    gpus = relationship("SQLGPU", secondary=network_gpus, back_populates="networks")
