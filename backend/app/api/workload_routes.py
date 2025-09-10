from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.workload import WorkloadCreate, Workload
from ..models.sql_workload import SQLWorkload

router = APIRouter()

@router.post("/workloads/submit", response_model=Workload, status_code=status.HTTP_201_CREATED)
def submit_workload(workload: WorkloadCreate, db: Session = Depends(get_db)):
    db_workload = SQLWorkload(**workload.dict())
    db.add(db_workload)
    db.commit()
    db.refresh(db_workload)
    return db_workload

@router.get("/workloads/status", response_model=List[Workload])
def get_workload_status(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    workloads = db.query(SQLWorkload).offset(skip).limit(limit).all()
    return workloads

@router.get("/workloads/{workload_id}/status", response_model=Workload)
def get_single_workload_status(workload_id: int, db: Session = Depends(get_db)):
    workload = db.query(SQLWorkload).filter(SQLWorkload.id == workload_id).first()
    if not workload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")
    return workload
