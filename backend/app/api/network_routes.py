from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from ..database import get_db
from ..models.network import Network, NetworkCreate
from ..models.sql_network import SQLNetwork
from ..models.sql_gpu import SQLGPU # Needed to find GPUs by UUID

router = APIRouter()

class MergeNetworksRequest(BaseModel):
    network_ids: List[int]
    new_network_name: str
    new_network_description: str = None

class SplitNetworkRequest(BaseModel):
    network_id: int
    gpu_uuids_to_move: List[str]
    new_network_name: str
    new_network_description: str = None

@router.post("/networks/merge", response_model=Network)
def merge_networks(request: MergeNetworksRequest, db: Session = Depends(get_db)):
    if len(request.network_ids) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least two networks are required to merge.")

    networks_to_merge = db.query(SQLNetwork).filter(SQLNetwork.id.in_(request.network_ids)).all()
    if len(networks_to_merge) != len(request.network_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more networks not found.")

    # Collect all unique GPUs from the networks to be merged
    all_gpus = set()
    for net in networks_to_merge:
        for gpu in net.gpus:
            all_gpus.add(gpu)

    # Create a new network
    new_network = SQLNetwork(name=request.new_network_name, description=request.new_network_description)
    db.add(new_network)
    db.flush() # To get the ID for the new_network

    # Add all collected GPUs to the new network
    for gpu in all_gpus:
        new_network.gpus.append(gpu)

    # Delete the old networks
    for net in networks_to_merge:
        db.delete(net)
    
    db.commit()
    db.refresh(new_network)
    return new_network

@router.post("/networks/split", response_model=List[Network])
def split_network(request: SplitNetworkRequest, db: Session = Depends(get_db)):
    original_network = db.query(SQLNetwork).filter(SQLNetwork.id == request.network_id).first()
    if not original_network:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original network not found.")

    gpus_to_move = db.query(SQLGPU).filter(SQLGPU.uuid.in_(request.gpu_uuids_to_move)).all()
    if len(gpus_to_move) != len(request.gpu_uuids_to_move):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more GPUs to move not found.")

    # Ensure all GPUs to move are actually in the original network
    original_network_gpu_uuids = {gpu.uuid for gpu in original_network.gpus}
    for gpu in gpus_to_move:
        if gpu.uuid not in original_network_gpu_uuids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"GPU {gpu.uuid} is not part of the original network.")

    # Create a new network for the moved GPUs
    new_network = SQLNetwork(name=request.new_network_name, description=request.new_network_description)
    db.add(new_network)
    db.flush()

    # Move GPUs from original network to new network
    for gpu in gpus_to_move:
        original_network.gpus.remove(gpu)
        new_network.gpus.append(gpu)
    
    db.commit()
    db.refresh(original_network)
    db.refresh(new_network)
    
    return [original_network, new_network]
