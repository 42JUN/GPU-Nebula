from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
import os

Base = declarative_base()

class Agent(Base):
    __tablename__ = 'agents'
    id = Column(Integer, primary_key=True)
    hostname = Column(String, unique=True, nullable=False)
    ip_address = Column(String)
    os = Column(String)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    gpus = relationship("GPU", back_populates="agent")
    jobs = relationship("Job", back_populates="agent")

class GPU(Base):
    __tablename__ = 'gpus'
    id = Column(String, primary_key=True)  # UUID
    agent_id = Column(Integer, ForeignKey('agents.id'))
    
    agent = relationship("Agent", back_populates="gpus")
    
    name = Column(String)
    model = Column(String)
    serial = Column(String)
    pci_bus_id = Column(String)
    driver_version = Column(String)
    
    # Real-time metrics (updated by gpu_detector.py)
    status = Column(String, default="healthy")
    temperature = Column(Integer)
    utilization = Column(Integer)  # GPU utilization %
    memory_total = Column(Integer)  # Total VRAM in MB
    memory_used = Column(Integer)   # Used VRAM in MB
    vram = Column(Integer)  # Keep for backward compatibility
    
    # Scheduling metadata
    is_available = Column(Boolean, default=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    jobs = relationship("Job", back_populates="gpu")

class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
    
    # Job metadata
    workload_type = Column(String)  # inference, training, fine-tuning, etc.
    command = Column(Text)  # Command to execute
    status = Column(String, default="pending")  # pending, running, completed, failed, queued
    
    # Resource assignment
    assigned_gpu_id = Column(String, ForeignKey('gpus.id'), nullable=True)
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=True)
    
    # Process tracking
    pid = Column(Integer, nullable=True)  # Process ID for local jobs
    
    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    
    # Legacy fields (keep for compatibility)
    type = Column(String)  # Maps to workload_type
    payload = Column(Text)  # Maps to command
    start_time = Column(DateTime(timezone=True))  # Maps to started_at
    end_time = Column(DateTime(timezone=True))  # Maps to finished_at
    
    # Relationships
    gpu = relationship("GPU", back_populates="jobs")
    agent = relationship("Agent", back_populates="jobs")
    history_entries = relationship("History", back_populates="job")

class History(Base):
    __tablename__ = 'history'
    id = Column(Integer, primary_key=True)
    action = Column(String)  # submitted, scheduled, started, completed, failed
    job_id = Column(Integer, ForeignKey('jobs.id'))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    details = Column(Text)  # JSON string for structured data
    
    job = relationship("Job", back_populates="history_entries")

class Network(Base):
    __tablename__ = 'networks'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    status = Column(String)

# Database setup
DB_PATH = "c:/dev/GPU-Nebula/backend/control_plane.db"
engine = create_engine(f'sqlite:///{DB_PATH}')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    print("Creating database tables...")
    # Only delete in development - comment out for production
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed old database file.")
    
    Base.metadata.create_all(engine)
    print("Tables created successfully!")

if __name__ == '__main__':
    create_tables()
