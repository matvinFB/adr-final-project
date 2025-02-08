import asyncio
import time
import json
import httpx
import os
from dotenv import load_dotenv
from modules.proxmox_vm_manager_module import ProxmoxVMManager
from modules.proxmox_monitor_module import ProxmoxMonitor
from modules.load_tester_module import run_load_test

# Carregar variáveis do .env
load_dotenv()

PROXMOX_IP = os.getenv("PROXMOX_IP")
PROXMOX_TOKEN = os.getenv("PROXMOX_TOKEN")
NODE = os.getenv("NODE")
VM_ID_1 = int(os.getenv("VM_ID_1"))  # Servidor 1 (Fixado com 1 núcleo)
VM_ID_2 = int(os.getenv("VM_ID_2"))  # Servidor 2 (Irá variar o número de núcleos)
LB_URL = os.getenv("LB_URL")
SERVER_1_CORES = 1
EXPERIMENT_DURATION = int(os.getenv("EXPERIMENT_DURATION", 30))

# Definição dos fatores
RPS_LEVELS = list(map(int, os.getenv("RPS_LEVELS", "100,1000,10000").split(',')))
CORE_LEVELS = list(map(int, os.getenv("CORE_LEVELS", "1,2,4,8").split(',')))
ALGORITHMS = os.getenv("ALGORITHMS", "round_robin,balanced_round_robin").split(',')

async def set_load_balancer_config(algorithm, cores_server2):
    """Atualiza a configuração do Load Balancer"""
    servers_config = [
        {"host": "192.168.1.2", "port": 8080, "weight": SERVER_1_CORES},
        {"host": "192.168.2.2", "port": 8080, "weight": cores_server2}
    ]

    if algorithm == "round_robin":
        servers_config = [{"host": s["host"], "port": s["port"], "weight": 1} for s in servers_config]
    
    async with httpx.AsyncClient() as client:
        await client.post(f"{LB_URL}/admin/config", json={"servers": servers_config})

async def run_experiment():
    for rps in RPS_LEVELS:
        for cores in CORE_LEVELS:
            for algorithm in ALGORITHMS:
                scenario_name = f"rps{rps}-cores{cores}-alg{algorithm}"
                log_request_file = f"logs/{scenario_name}-requests.txt"
                log_monitor_file_1 = f"logs/{scenario_name}-vm1-monitoring.txt"
                log_monitor_file_2 = f"logs/{scenario_name}-vm2-monitoring.txt"
                os.makedirs("logs", exist_ok=True)

                print(f"\n=== Executando cenário: {scenario_name} ===")

                # Atualizar núcleos do servidor 2
                vm_manager = ProxmoxVMManager(PROXMOX_IP, PROXMOX_TOKEN, NODE, VM_ID_2)
                vm_manager.update_vm_cores(cores)

                # Configurar Load Balancer
                await set_load_balancer_config(algorithm, cores)

                # Iniciar Monitoramento (2s antes) para ambos os servidores
                monitor_1 = ProxmoxMonitor(PROXMOX_IP, PROXMOX_TOKEN, NODE, VM_ID_1, log_monitor_file_1)
                monitor_2 = ProxmoxMonitor(PROXMOX_IP, PROXMOX_TOKEN, NODE, VM_ID_2, log_monitor_file_2)
                monitor_task_1 = asyncio.create_task(monitor_1.monitor(interval=1, duration=EXPERIMENT_DURATION + 4))
                monitor_task_2 = asyncio.create_task(monitor_2.monitor(interval=1, duration=EXPERIMENT_DURATION + 4))
                await asyncio.sleep(2)

                # Iniciar Teste de Carga
                await run_load_test(base_url=LB_URL, rps=rps, duration=EXPERIMENT_DURATION, log_file=log_request_file)

                # Esperar monitoramento terminar
                await asyncio.sleep(2)
                monitor_task_1.cancel()
                monitor_task_2.cancel()
                print(f"Cenário {scenario_name} concluído!\n")

if __name__ == "__main__":
    asyncio.run(run_experiment())
