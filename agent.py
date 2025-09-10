import requests
import time
import platform
import socket
from gpu_detector import GPUDetector

# --- Configuration ---
# In a real app, this would come from a config file or environment variables
CONTROL_PLANE_URL = "http://127.0.0.1:8000/api/v1/agent/report-in"
REPORT_INTERVAL = 30  # seconds

class GPUAgent:
    def __init__(self):
        self.hostname = socket.gethostname()
        self.gpu_detector = GPUDetector()
        print(f"🚀 GPU Agent starting on host: {self.hostname}")

    def get_system_info(self):
        """Gathers basic information about the host system."""
        return {
            "hostname": self.hostname,
            "ip_address": socket.gethostbyname(self.hostname),
            "os": f"{platform.system()} {platform.release()}",
        }

    def run(self):
        """The main loop for the agent."""
        while True:
            print("🔍 Detecting local GPUs...")
            try:
                gpu_data = self.gpu_detector.detect_gpus()
                system_info = self.get_system_info()

                # Combine system info and GPU data into a single report
                report = {
                    "agent_info": system_info,
                    "gpu_report": gpu_data
                }

                print(f"🛰️ Sending report to Control Plane at {CONTROL_PLANE_URL}...")
                response = requests.post(CONTROL_PLANE_URL, json=report, timeout=10)

                if response.status_code == 200:
                    print(f"✅ Report accepted by Control Plane: {response.json().get('message')}")
                else:
                    print(f"❌ Report rejected by Control Plane (HTTP {response.status_code}): {response.text}")

            except requests.exceptions.RequestException as e:
                print(f"❌ Could not connect to Control Plane: {e}")
            except Exception as e:
                print(f"❌ An error occurred: {e}")
            
            print(f"😴 Sleeping for {REPORT_INTERVAL} seconds...")
            time.sleep(REPORT_INTERVAL)

if __name__ == "__main__":
    agent = GPUAgent()
    agent.run()
