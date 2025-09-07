from typing import Union 
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback

# Setup FastAPI app
app = FastAPI(title="GPU Nebula Backend", version="1.0.0", description="Advanced GPU Cluster Management API")

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import enhanced GPU detector
from gpu_detector import gpu_detector

# Initialize GPU detection
print("🔍 Initializing Enhanced GPU Detection System...")
gpu_detection_result = gpu_detector.detect_gpus()
NVML_AVAILABLE = gpu_detection_result.get('detection_method') == 'nvidia_nvml'
print(f"✅ GPU Detection Complete - Method: {gpu_detection_result.get('detection_method', 'unknown')}")


# Legacy functions removed - now using enhanced GPU detector


def get_topology():
    """Get GPU topology using enhanced detection system"""
    try:
        print("🔍 Getting GPU topology...")
        
        # Use the enhanced GPU detector
        result = gpu_detector.detect_gpus()
        
        # Add timestamp
        result["timestamp"] = "2024-09-07T15:30:00Z"
        
        print(f"✅ Topology retrieved: {len(result.get('gpus', []))} GPUs, {len(result.get('servers', []))} servers")
        return result
        
    except Exception as e:
        print(f"❌ Error in get_topology: {e}")
        traceback.print_exc()
        return {
            "gpus": [],
            "servers": [],
            "connections": [],
            "timestamp": "2024-09-07T15:30:00Z",
            "status": "error",
            "error": str(e)
        }
    


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "🚀 GPU Nebula Backend API",
        "version": "1.0.0",
        "status": "online",
        "nvml_available": NVML_AVAILABLE,
        "endpoints": {
            "topology": "/topology",
            "gpu_list": "/gpu/list",
            "gpu_self": "/gpu/self",
            "docs": "/docs"
        }
    }

@app.get("/topology")
async def topology():
    """Get GPU cluster topology data"""
    try:
        data = get_topology()
        print(f"📤 Sending topology data: {len(data.get('gpus', []))} GPUs, {len(data.get('servers', []))} servers")
        return JSONResponse(content=data)
    except Exception as e:
        print(f"❌ Error in topology endpoint: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(e),
                "status": "error"
            }
        )

@app.get("/gpu/list")
async def gpu_list():
    """Return detailed GPU list using enhanced detection"""
    try:
        result = gpu_detector.detect_gpus()
        return {
            "status": "success", 
            "gpus": result.get("gpus", []),
            "detection_method": result.get("detection_method", "unknown")
        }
    except Exception as e:
        print(f"❌ Error in /gpu/list: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/gpu/self")
async def gpu_self():
    """Return details for the primary GPU using enhanced detection"""
    try:
        # Get fresh GPU detection
        result = gpu_detector.detect_gpus()
        gpus = result.get("gpus", [])
        
        if gpus:
            primary_gpu = gpus[0]
            return {
                "status": "success", 
                "gpu": primary_gpu,
                "detection_method": result.get("detection_method", "unknown")
            }
        else:
            return {"status": "no_gpu", "message": "No GPU detected"}
            
    except Exception as e:
        print(f"❌ Error in /gpu/self: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/gpu/detect")
async def detect_my_gpu():
    """Force detection of user's GPU and save to database"""
    try:
        print("🔍 Force detecting user's GPU...")
        
        # Get fresh detection
        result = gpu_detector.detect_gpus()
        gpus = result.get("gpus", [])
        
        if not gpus:
            return JSONResponse(
                status_code=404, 
                content={"status": "error", "message": "No GPUs detected"}
            )
        
        # Save to database
        from sqlalchemy import create_engine, text, func
        from sqlalchemy.orm import sessionmaker
        from create_db import GPU, Network, Job, History, Base
        
        engine = create_engine('sqlite:///control_plane.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Clear existing GPU data
            session.query(GPU).delete()
            session.query(Network).delete()
            
            # Create default network
            network = Network(name="Local Network", status="active")
            session.add(network)
            session.flush()  # Get the network ID
            
            # Add detected GPUs
            for gpu_data in gpus:
                gpu = GPU(
                    name=gpu_data["name"],
                    network_id=network.id,
                    status=gpu_data["status"],
                    temperature=gpu_data["temperature"],
                    utilization=gpu_data["utilization"],
                    connections=1,  # Default connection count
                    vram=gpu_data["memoryTotal"] // (1024**3)  # Convert to GB
                )
                session.add(gpu)
            
            # Add detection history
            history = History(
                action="GPU_DETECTION",
                timestamp=func.now(),
                details=f"Detected {len(gpus)} GPU(s) using {result.get('detection_method', 'unknown')} method"
            )
            session.add(history)
            
            session.commit()
            
            return {
                "status": "success",
                "message": f"Detected and saved {len(gpus)} GPU(s)",
                "gpus": gpus,
                "detection_method": result.get("detection_method", "unknown")
            }
            
        except Exception as db_error:
            session.rollback()
            print(f"Database error: {db_error}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"Database error: {str(db_error)}"}
            )
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Error in /gpu/detect: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2024-08-27T19:13:11Z",
        "nvml_available": NVML_AVAILABLE
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting GPU Nebula Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
