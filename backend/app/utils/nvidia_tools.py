import subprocess
from typing import Optional, List, Dict

def run_nvidia_smi_query(query: str, format: str = "csv,noheader,nounits") -> Optional[List[str]]:
    """
    Runs an nvidia-smi query and returns the raw output lines.
    """
    try:
        command = [
            "nvidia-smi",
            f"--query-gpu={query}",
            f"--format={format}"
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')
    except FileNotFoundError:
        print("nvidia-smi not found. Please ensure NVIDIA drivers are installed.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error running nvidia-smi: {e.stderr}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def get_gpu_uuids() -> List[str]:
    """Returns a list of UUIDs of all detected NVIDIA GPUs."""
    uuids = []
    raw_data = run_nvidia_smi_query("uuid")
    if raw_data:
        uuids = [line.strip() for line in raw_data if line.strip()]
    return uuids

# Placeholder for pynvml integration
def get_nvml_gpu_details(uuid: str) -> Optional[Dict]:
    """
    (Placeholder) Retrieves detailed GPU information using pynvml.
    Requires nvidia-ml-py3 to be installed.
    """
    print(f"Using pynvml to get details for GPU: {uuid} (Not yet implemented)")
    return None
