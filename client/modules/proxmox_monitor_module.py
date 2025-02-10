import time
import datetime
import urllib3
import requests

class ProxmoxMonitor:
    def __init__(self, ip, token, node, vm_id, log_file=None):
        """
        Initialize the ProxmoxMonitor instance.
        
        :param ip: Proxmox server IP or domain
        :param token: API Token in format 'USER@REALM!TOKEN_NAME=TOKEN_VALUE'
        :param node: Proxmox node name
        :param vm_id: ID of the VM to monitor
        :param log_file: (Optional) File path to save logs
        """
        self.proxmox_url = f"https://{ip}:8006"
        self.headers = {"Authorization": f"PVEAPIToken={token}"}
        self.node = node
        self.vm_id = vm_id
        self.log_file = log_file
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def get_usage(self):
        """
        Fetch the CPU and RAM usage from Proxmox API.

        :return: Dictionary with CPU (%) and RAM (MB) usage
        """
        url = f"{self.proxmox_url}/api2/json/nodes/{self.node}/qemu/{self.vm_id}/status/current"

        try:
            response = requests.get(url, headers=self.headers, verify=False, timeout=5)

            if response.status_code == 200:
                data = response.json().get("data", {})

                # CPU Calculation (No need to multiply by vcpus)
                cpu_percentage = round(data.get("cpu", 0), 6)

                # RAM Calculation
                ram_used = round(data.get("mem", 0) / (1024 * 1024), 2)  # Convert bytes to MB
                ram_total = round(data.get("maxmem", 1) / (1024 * 1024), 2)  # Convert bytes to MB
                ram_percentage = round((ram_used / ram_total) * 100, 2) if ram_total > 0 else 0

                usage = {
                    "cpu": cpu_percentage,
                    "ram": ram_percentage,
                    "ram_used_mb": ram_used,
                    "ram_total_mb": ram_total
                }

                # Log to file if needed
                if self.log_file:
                    with open(self.log_file, "a") as log:
                        log_entry = f"{datetime.datetime.now()} - CPU: {cpu_percentage} | RAM: {ram_percentage}% ({ram_used}/{ram_total} MB)\n"
                        log.write(log_entry)

                return usage

            else:
                print(f"[ERROR] Proxmox API returned {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Connection issue: {e}")
            return None

    def monitor(self, interval=1//5, duration=None):
        """
        Continuously monitor CPU and RAM usage at a given interval.

        :param interval: Time (in seconds) between requests
        :param duration: (Optional) Number of seconds to run before stopping
        """
        print(f"Starting monitoring for VM {self.vm_id} on {self.node}... (Press CTRL+C to stop)")
        
        try:
            start_time = time.time()

            while duration is None or (time.time() - start_time) < duration:
                usage = self.get_usage()
                #if usage:
                    #print(f"CPU: {usage['cpu']}% | RAM: {usage['ram']}% ({usage['ram_used_mb']}/{usage['ram_total_mb']} MB)")
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\nMonitoring stopped by user.")
