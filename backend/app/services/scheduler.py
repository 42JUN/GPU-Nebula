from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from ..models.workload import Workload
from ..models.sql_workload import SQLWorkload
from ..models.sql_gpu import SQLGPU, SQLGPUMetrics
from ..models.topology import Topology # To consider topology in future

def find_available_gpu(db: Session, workload_requirements: dict) -> Optional[SQLGPU]:
    """
    Finds an available GPU that meets the workload's resource requirements.
    For now, a very basic implementation: finds any GPU not currently running a workload.
    Future: Consider topology, actual resource availability (memory, utilization).
    """
    # Find GPUs that are not currently assigned to a running workload
    # This is a simplified check. A more robust check would involve:
    # - Checking actual GPU utilization and memory
    # - Considering the workload's specific resource_requirements
    
    # Get all registered GPUs
    all_gpus = db.query(SQLGPU).all()

    # Get UUIDs of GPUs currently running workloads
    running_workload_gpu_uuids = {
        w.assigned_gpu_uuid for w in db.query(SQLWorkload).filter(SQLWorkload.status == "running").all()
        if w.assigned_gpu_uuid
    }

    for gpu in all_gpus:
        if gpu.uuid not in running_workload_gpu_uuids:
            # Basic check: if GPU is not running any workload, consider it available
            # Future: Add more sophisticated checks based on workload_requirements
            # e.g., check if gpu.memory_total_mb >= workload_requirements.get("gpu_memory_gb", 0) * 1024
            return gpu
    return None

def schedule_workload(db: Session, workload_id: int) -> Optional[Workload]:
    """
    Schedules a specific workload to an available GPU.
    """
    workload = db.query(SQLWorkload).filter(SQLWorkload.id == workload_id).first()
    if not workload:
        return None

    if workload.status != "pending":
        print(f"Workload {workload.id} is not in 'pending' status. Skipping scheduling.")
        return Workload.from_orm(workload)

    available_gpu = find_available_gpu(db, workload.resource_requirements)

    if available_gpu:
        workload.assigned_gpu_uuid = available_gpu.uuid
        workload.status = "running"
        workload.started_at = datetime.now()
        db.add(workload)
        db.commit()
        db.refresh(workload)
        print(f"Workload {workload.id} scheduled to GPU {available_gpu.uuid}")
        return Workload.from_orm(workload)
    else:
        print(f"No available GPU found for workload {workload.id}. Workload remains pending.")
        return Workload.from_orm(workload)

def complete_workload(db: Session, workload_id: int) -> Optional[Workload]:
    """
    Marks a workload as completed.
    """
    workload = db.query(SQLWorkload).filter(SQLWorkload.id == workload_id).first()
    if not workload:
        return None
    
    workload.status = "completed"
    workload.completed_at = datetime.now()
    db.add(workload)
    db.commit()
    db.refresh(workload)
    print(f"Workload {workload.id} completed.")
    return Workload.from_orm(workload)
