from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
import os

# Define the base for your models
Base = declarative_base()

# --- Define the Tables as Python Classes ---

class Agent(Base):
    __tablename__ = 'agents'
    id = Column(Integer, primary_key=True)
    hostname = Column(String, unique=True, nullable=False)
    ip_address = Column(String)
    os = Column(String)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    gpus = relationship("GPU", back_populates="agent")

class GPU(Base):
    __tablename__ = 'gpus'
    id = Column(String, primary_key=True) # UUID
    agent_id = Column(Integer, ForeignKey('agents.id'))
    agent = relationship("Agent", back_populates="gpus")
    
    name = Column(String)
    model = Column(String)
    serial = Column(String)
    pci_bus_id = Column(String)
    driver_version = Column(String)
    network_id = Column(Integer, ForeignKey('networks.id'))
    status = Column(String, default="healthy")
    temperature = Column(Integer)
    utilization = Column(Integer)
    vram = Column(Integer)

class Network(Base):
    __tablename__ = 'networks'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    status = Column(String)

class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
    type = Column(String)
    payload = Column(Text)
    status = Column(String, default="pending")
    assigned_gpu_id = Column(String, ForeignKey('gpus.id'), nullable=True)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))

class History(Base):
    __tablename__ = 'history'
    id = Column(Integer, primary_key=True)
    action = Column(String)
    job_id = Column(Integer, ForeignKey('jobs.id'))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    details = Column(String)

# --- Connect to the Database and Create the Tables ---

engine = create_engine('sqlite:///control_plane.db')

def create_tables():
    print("Creating database tables...")
    if os.path.exists('control_plane.db'):
        os.remove('control_plane.db')
        print("Removed old database file.")
    Base.metadata.create_all(engine)
    print("Tables created successfully!")

if __name__ == '__main__':
    create_tables()