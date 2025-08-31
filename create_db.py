from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
import os

# Define the base for your models
Base = declarative_base()

# --- Define the Tables as Python Classes ---

class GPU(Base):
    __tablename__ = 'gpus'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    network_id = Column(Integer, ForeignKey('networks.id'))
    status = Column(String)
    temperature = Column(Integer)
    utilization = Column(Integer)
    connections = Column(Integer)
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
    assigned_gpu_id = Column(Integer, ForeignKey('gpus.id'))
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

# The line below creates a SQLite database file named 'control_plane.db'
engine = create_engine('sqlite:///control_plane.db')

# This command creates all the tables you defined above in the database
def create_tables():
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("Tables created successfully!")

# Run the function when the script is executed
if __name__ == '__main__':
    create_tables()