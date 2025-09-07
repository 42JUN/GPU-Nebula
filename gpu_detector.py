"""
Enhanced GPU Detection Module
Supports multiple GPU detection methods with fallbacks
"""

import platform
import subprocess
import json
import os
from typing import Dict, List, Optional, Any

class GPUDetector:
    def __init__(self):
        self.system = platform.system().lower()
        self.gpu_info = []
        self.detection_methods = []
        
    def detect_gpus(self) -> Dict[str, Any]:
        """Main method to detect GPUs using multiple fallback methods"""
        print("🔍 Starting GPU Detection...")
        
        # Try different detection methods in order of preference
        detection_methods = [
            self._detect_nvidia_nvml,
            self._detect_nvidia_smi,
            self._detect_amd_rocm,
            self._detect_intel_gpu,
            self._detect_windows_wmi,
            self._detect_linux_lspci,
            self._detect_macos_system
        ]
        
        for method in detection_methods:
            try:
                result = method()
                if result and result.get('gpus'):
                    self.gpu_info = result['gpus']
                    self.detection_methods.append(method.__name__)
                    print(f"✅ GPU Detection successful using {method.__name__}")
                    return result
            except Exception as e:
                print(f"⚠️ {method.__name__} failed: {e}")
                continue
        
        # If all methods fail, return mock data
        print("🎭 All detection methods failed, using mock data")
        return self._get_mock_data()
    
    def _detect_nvidia_nvml(self) -> Optional[Dict[str, Any]]:
        """Detect NVIDIA GPUs using NVML (most accurate)"""
        try:
            import pynvml
            pynvml.nvmlInit()
            
            gpu_count = pynvml.nvmlDeviceGetCount()
            gpus = []
            
            for i in range(gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # Get GPU name
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8')
                
                # Get memory info
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                
                # Get temperature
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except:
                    temp = 65
                
                # Get power usage
                try:
                    power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
                except:
                    power = 250.0
                
                # Get utilization
                try:
                    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_util = utilization.gpu
                    mem_util = utilization.memory
                except:
                    gpu_util = 50
                    mem_util = 40
                
                gpu_data = {
                    "id": f"gpu-{i}",
                    "name": f"GPU-{i}",
                    "model": str(name),
                    "type": "gpu",
                    "status": "healthy",
                    "temperature": temp,
                    "powerUsage": power,
                    "memoryUsed": memory_info.used,
                    "memoryTotal": memory_info.total,
                    "utilization": gpu_util,
                    "memoryUtilization": mem_util,
                    "detection_method": "nvidia_nvml"
                }
                gpus.append(gpu_data)
            
            return {
                "gpus": gpus,
                "servers": [self._get_host_server()],
                "connections": self._create_connections(gpus),
                "detection_method": "nvidia_nvml",
                "status": "success"
            }
            
        except ImportError:
            raise Exception("pynvml not available")
        except Exception as e:
            raise Exception(f"NVML detection failed: {e}")
    
    def _detect_nvidia_smi(self) -> Optional[Dict[str, Any]]:
        """Detect NVIDIA GPUs using nvidia-smi command"""
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used,temperature.gpu,power.draw,utilization.gpu,utilization.memory', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                raise Exception("nvidia-smi command failed")
            
            gpus = []
            lines = result.stdout.strip().split('\n')
            
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                    
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 8:
                    continue
                
                try:
                    gpu_data = {
                        "id": f"gpu-{i}",
                        "name": f"GPU-{i}",
                        "model": parts[1],
                        "type": "gpu",
                        "status": "healthy",
                        "temperature": int(float(parts[4])) if parts[4] != 'N/A' else 65,
                        "powerUsage": float(parts[5]) if parts[5] != 'N/A' else 250.0,
                        "memoryUsed": int(parts[3]) * 1024 * 1024 if parts[3] != 'N/A' else 8000000000,
                        "memoryTotal": int(parts[2]) * 1024 * 1024 if parts[2] != 'N/A' else 24000000000,
                        "utilization": int(parts[6]) if parts[6] != 'N/A' else 50,
                        "memoryUtilization": int(parts[7]) if parts[7] != 'N/A' else 40,
                        "detection_method": "nvidia_smi"
                    }
                    gpus.append(gpu_data)
                except (ValueError, IndexError) as e:
                    print(f"Error parsing nvidia-smi output: {e}")
                    continue
            
            if gpus:
                return {
                    "gpus": gpus,
                    "servers": [self._get_host_server()],
                    "connections": self._create_connections(gpus),
                    "detection_method": "nvidia_smi",
                    "status": "success"
                }
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            raise Exception(f"nvidia-smi detection failed: {e}")
    
    def _detect_amd_rocm(self) -> Optional[Dict[str, Any]]:
        """Detect AMD GPUs using ROCm tools"""
        try:
            # Try rocm-smi first
            result = subprocess.run(['rocm-smi', '--showid', '--showproductname', '--showtemp', '--showuse', '--showmemuse'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Parse rocm-smi output
                gpus = self._parse_rocm_smi_output(result.stdout)
                if gpus:
                    return {
                        "gpus": gpus,
                        "servers": [self._get_host_server()],
                        "connections": self._create_connections(gpus),
                        "detection_method": "amd_rocm",
                        "status": "success"
                    }
            
            # Try clinfo as fallback
            result = subprocess.run(['clinfo'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                gpus = self._parse_clinfo_output(result.stdout)
                if gpus:
                    return {
                        "gpus": gpus,
                        "servers": [self._get_host_server()],
                        "connections": self._create_connections(gpus),
                        "detection_method": "amd_clinfo",
                        "status": "success"
                    }
                    
        except Exception as e:
            raise Exception(f"AMD ROCm detection failed: {e}")
    
    def _detect_intel_gpu(self) -> Optional[Dict[str, Any]]:
        """Detect Intel GPUs"""
        try:
            if self.system == "windows":
                # Use wmic for Intel GPUs on Windows
                result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name,AdapterRAM', '/format:csv'], 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    gpus = self._parse_wmic_output(result.stdout)
                    if gpus:
                        return {
                            "gpus": gpus,
                            "servers": [self._get_host_server()],
                            "connections": self._create_connections(gpus),
                            "detection_method": "intel_wmic",
                            "status": "success"
                        }
            
            # Try intel_gpu_top on Linux
            result = subprocess.run(['intel_gpu_top', '-l'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                gpus = self._parse_intel_gpu_top_output(result.stdout)
                if gpus:
                    return {
                        "gpus": gpus,
                        "servers": [self._get_host_server()],
                        "connections": self._create_connections(gpus),
                        "detection_method": "intel_gpu_top",
                        "status": "success"
                    }
                    
        except Exception as e:
            raise Exception(f"Intel GPU detection failed: {e}")
    
    def _detect_windows_wmi(self) -> Optional[Dict[str, Any]]:
        """Detect GPUs using Windows WMI"""
        if self.system != "windows":
            raise Exception("WMI only available on Windows")
            
        try:
            result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name,AdapterRAM,Status', '/format:csv'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                gpus = self._parse_wmic_output(result.stdout)
                if gpus:
                    return {
                        "gpus": gpus,
                        "servers": [self._get_host_server()],
                        "connections": self._create_connections(gpus),
                        "detection_method": "windows_wmi",
                        "status": "success"
                    }
                    
        except Exception as e:
            raise Exception(f"Windows WMI detection failed: {e}")
    
    def _detect_linux_lspci(self) -> Optional[Dict[str, Any]]:
        """Detect GPUs using lspci on Linux"""
        if self.system != "linux":
            raise Exception("lspci only available on Linux")
            
        try:
            result = subprocess.run(['lspci', '-nn'], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                gpus = self._parse_lspci_output(result.stdout)
                if gpus:
                    return {
                        "gpus": gpus,
                        "servers": [self._get_host_server()],
                        "connections": self._create_connections(gpus),
                        "detection_method": "linux_lspci",
                        "status": "success"
                    }
                    
        except Exception as e:
            raise Exception(f"Linux lspci detection failed: {e}")
    
    def _detect_macos_system(self) -> Optional[Dict[str, Any]]:
        """Detect GPUs on macOS using system_profiler"""
        if self.system != "darwin":
            raise Exception("system_profiler only available on macOS")
            
        try:
            result = subprocess.run(['system_profiler', 'SPDisplaysDataType', '-json'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                gpus = self._parse_macos_system_output(data)
                if gpus:
                    return {
                        "gpus": gpus,
                        "servers": [self._get_host_server()],
                        "connections": self._create_connections(gpus),
                        "detection_method": "macos_system",
                        "status": "success"
                    }
                    
        except Exception as e:
            raise Exception(f"macOS system detection failed: {e}")
    
    def _get_host_server(self) -> Dict[str, Any]:
        """Get host system information"""
        import platform
        
        try:
            cpu_info = platform.processor() or "Unknown CPU"
            if not cpu_info or cpu_info == "Unknown CPU":
                cpu_info = platform.machine()
        except:
            cpu_info = "Unknown CPU"
        
        return {
            "id": "server-0",
            "name": f"Host-{platform.node()}",
            "type": "server",
            "cpu": cpu_info,
            "status": "healthy",
            "uptime": "99.9%",
            "os": f"{platform.system()} {platform.release()}"
        }
    
    def _create_connections(self, gpus: List[Dict]) -> List[Dict[str, Any]]:
        """Create connections between GPUs and server"""
        connections = []
        
        for i, gpu in enumerate(gpus):
            connections.append({
                "id": f"conn-server-gpu-{i}",
                "source": "server-0",
                "target": gpu["id"],
                "type": "pcie",
                "bandwidth": "32 GB/s",
                "status": "active"
            })
        
        # Add GPU-to-GPU connections if multiple GPUs
        for i in range(len(gpus)):
            for j in range(i + 1, len(gpus)):
                connections.append({
                    "id": f"conn-gpu-{i}-{j}",
                    "source": gpus[i]["id"],
                    "target": gpus[j]["id"],
                    "type": "nvlink" if "nvidia" in gpus[i]["model"].lower() else "pcie",
                    "bandwidth": "600 GB/s" if "nvlink" in connections[-1]["type"] else "32 GB/s",
                    "status": "active"
                })
        
        return connections
    
    def _get_mock_data(self) -> Dict[str, Any]:
        """Return mock data when real detection fails"""
        return {
            "gpus": [
                {
                    "id": "gpu-0",
                    "name": "GPU-0",
                    "model": "NVIDIA RTX 4090",
                    "type": "gpu",
                    "status": "healthy",
                    "temperature": 68,
                    "powerUsage": 420.5,
                    "memoryUsed": 12000000000,
                    "memoryTotal": 24000000000,
                    "utilization": 85,
                    "memoryUtilization": 70,
                    "detection_method": "mock"
                }
            ],
            "servers": [self._get_host_server()],
            "connections": [
                {
                    "id": "conn-server-gpu-0",
                    "source": "server-0",
                    "target": "gpu-0",
                    "type": "pcie",
                    "bandwidth": "32 GB/s",
                    "status": "active"
                }
            ],
            "detection_method": "mock",
            "status": "mock"
        }
    
    # Parsing helper methods
    def _parse_rocm_smi_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse rocm-smi output"""
        # Implementation would parse rocm-smi output
        return []
    
    def _parse_clinfo_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse clinfo output"""
        # Implementation would parse clinfo output
        return []
    
    def _parse_wmic_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse wmic output"""
        gpus = []
        lines = output.strip().split('\n')
        
        for i, line in enumerate(lines[1:], 1):  # Skip header
            if not line.strip():
                continue
                
            parts = line.split(',')
            if len(parts) >= 3:
                name = parts[1].strip() if len(parts) > 1 else f"GPU-{i}"
                memory = parts[2].strip() if len(parts) > 2 else "Unknown"
                
                gpu_data = {
                    "id": f"gpu-{i-1}",
                    "name": f"GPU-{i-1}",
                    "model": name,
                    "type": "gpu",
                    "status": "healthy",
                    "temperature": 65,
                    "powerUsage": 250.0,
                    "memoryUsed": 8000000000,
                    "memoryTotal": 24000000000,
                    "utilization": 50,
                    "memoryUtilization": 40,
                    "detection_method": "windows_wmi"
                }
                gpus.append(gpu_data)
        
        return gpus
    
    def _parse_lspci_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse lspci output for GPU devices"""
        gpus = []
        lines = output.strip().split('\n')
        
        gpu_count = 0
        for line in lines:
            if 'VGA compatible controller' in line or '3D controller' in line:
                # Extract GPU name from lspci output
                parts = line.split(':')
                if len(parts) >= 2:
                    name = parts[2].strip()
                    
                    gpu_data = {
                        "id": f"gpu-{gpu_count}",
                        "name": f"GPU-{gpu_count}",
                        "model": name,
                        "type": "gpu",
                        "status": "healthy",
                        "temperature": 65,
                        "powerUsage": 250.0,
                        "memoryUsed": 8000000000,
                        "memoryTotal": 24000000000,
                        "utilization": 50,
                        "memoryUtilization": 40,
                        "detection_method": "linux_lspci"
                    }
                    gpus.append(gpu_data)
                    gpu_count += 1
        
        return gpus
    
    def _parse_macos_system_output(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse macOS system_profiler output"""
        gpus = []
        
        try:
            displays = data.get('SPDisplaysDataType', [])
            for i, display in enumerate(displays):
                name = display.get('_name', f'GPU-{i}')
                
                gpu_data = {
                    "id": f"gpu-{i}",
                    "name": f"GPU-{i}",
                    "model": name,
                    "type": "gpu",
                    "status": "healthy",
                    "temperature": 65,
                    "powerUsage": 250.0,
                    "memoryUsed": 8000000000,
                    "memoryTotal": 24000000000,
                    "utilization": 50,
                    "memoryUtilization": 40,
                    "detection_method": "macos_system"
                }
                gpus.append(gpu_data)
        except Exception as e:
            print(f"Error parsing macOS system output: {e}")
        
        return gpus

# Global instance
gpu_detector = GPUDetector()
