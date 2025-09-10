from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from ..models.sql_gpu import SQLGPU, SQLGPUMetrics
from ..models.sql_workload import SQLWorkload
from .scheduler import schedule_workload # To reallocate tasks

# Configurable thresholds
THERMAL_THRESHOLD_CELSIUS = 85.0
UTILIZATION_THRESHOLD_PERCENT = 95.0
METRIC_CHECK_INTERVAL_SECONDS = 60 # How often to check metrics for faults

def check_gpu_faults(db: Session) -> List[str]:
    """
    Checks for GPU faults based on predefined thresholds.
    Returns a list of UUIDs of faulty GPUs.
    """
    faulty_gpus = []
    gpus = db.query(SQLGPU).all()

    for gpu in gpus:
        # Get the latest metrics for the GPU
        latest_metric = db.query(SQLGPUMetrics)\
            .filter(SQLGPUMetrics.gpu_id == gpu.id)\
            .order_by(SQLGPUMetrics.timestamp.desc())\
            .first()

        if latest_metric:
            if latest_metric.temperature_gpu and latest_metric.temperature_gpu > THERMAL_THRESHOLD_CELSIUS:
                print(f"Fault detected on GPU {gpu.uuid}: High temperature ({latest_metric.temperature_gpu}°C)")
                faulty_gpus.append(gpu.uuid)
            
            # Add other fault conditions here (e.g., sustained high utilization, memory errors)
            # if latest_metric.utilization_gpu and latest_metric.utilization_gpu > UTILIZATION_THRESHOLD_PERCENT:
            #     print(f"Fault detected on GPU {gpu.uuid}: High utilization ({latest_metric.utilization_gpu}%) ")
            #     faulty_gpus.append(gpu.uuid)
        else:
            print(f"No metrics found for GPU {gpu.uuid}. Cannot check for faults.")

    return faulty_gpus

def reallocate_workloads_from_faulty_gpus(db: Session, faulty_gpu_uuids: List[str]):
    """
    Reallocates workloads from faulty GPUs.
    """
    for gpu_uuid in faulty_gpu_uuids:
        workloads_on_faulty_gpu = db.query(SQLWorkload)\
            .filter(SQLWorkload.assigned_gpu_uuid == gpu_uuid, SQLWorkload.status == "running")\
            .all()
        
        for workload in workloads_on_faulty_gpu:
            print(f"Reallocating workload {workload.id} from faulty GPU {gpu_uuid}")
            workload.status = "pending" # Mark as pending for rescheduling
            workload.assigned_gpu_uuid = None
            db.add(workload)
            db.commit()
            db.refresh(workload)
            
            # Attempt to reschedule the workload
            scheduled_workload = schedule_workload(db, workload.id)
            if scheduled_workload and scheduled_workload.status == "running":
                print(f"Workload {workload.id} successfully reallocated to {scheduled_workload.assigned_gpu_uuid}")
            else:
                print(f"Failed to reallocate workload {workload.id}. It remains pending.")
