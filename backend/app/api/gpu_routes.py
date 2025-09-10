from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.gpu import GPUCreate, GPU, GPUMetrics
from ..models.sql_gpu import SQLGPU, SQLGPUMetrics

router = APIRouter()

@router.post("/agents/register", response_model=GPU, status_code=status.HTTP_201_CREATED)
def register_gpu_agent(gpu: GPUCreate, db: Session = Depends(get_db)):
    db_gpu = db.query(SQLGPU).filter(SQLGPU.uuid == gpu.uuid).first()
    if db_gpu:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GPU with this UUID already registered")
    
    db_gpu = SQLGPU(**gpu.dict())
    db.add(db_gpu)
    db.commit()
    db.refresh(db_gpu)
    return db_gpu

@router.get("/gpus", response_model=List[GPU])
def list_gpus(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    gpus = db.query(SQLGPU).offset(skip).limit(limit).all()
    return gpus

@router.get("/gpus/{gpu_id}/metrics", response_model=List[GPUMetrics])
def get_gpu_metrics(gpu_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    gpu = db.query(SQLGPU).filter(SQLGPU.id == gpu_id).first()
    if not gpu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GPU not found")
    
    metrics = db.query(SQLGPUMetrics).filter(SQLGPUMetrics.gpu_id == gpu_id).offset(skip).limit(limit).all()
    return metrics
