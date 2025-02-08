import asyncio
import time
import json
import httpx
import os
from modules.proxmox_vm_manager_module import ProxmoxVMManager
from modules.proxmox_monitor_module import ProxmoxMonitor
from modules.load_tester_module import run_load_test

# Configurações
PROXMOX_IP = "192.168.1.100"
PROXMOX_TOKEN = "USER@REALM!TOKEN_NAME=TOKEN_VALUE"
NODE = "pve"
VM_ID = 102  # Servidor 2 (O Servidor 1 tem sempre 1 núcleo)
LB_URL = "http://192.168.1.200:8080"
SERVER_1_CORES = 1
EXPERIMENT_DURATION = 30  # Duração do teste em segundos

# Definição dos fatores
RPS_LEVELS = [100, 1000, 10000]
CORE_LEVELS = [1, 2, 4, 8]
ALGORITHMS = ["round_robin", "balanced_round_robin"]

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
                log_monitor_file = f"logs/{scenario_name}-vm-monitoring.txt"
                os.makedirs("logs", exist_ok=True)

                print(f"\n=== Executando cenário: {scenario_name} ===")

                # Atualizar núcleos do servidor 2
                vm_manager = ProxmoxVMManager(PROXMOX_IP, PROXMOX_TOKEN, NODE, VM_ID)
                vm_manager.update_vm_cores(cores)

                # Configurar Load Balancer
                await set_load_balancer_config(algorithm, cores)

                # Iniciar Monitoramento (2s antes)
                monitor = ProxmoxMonitor(PROXMOX_IP, PROXMOX_TOKEN, NODE, VM_ID, log_monitor_file)
                monitor_task = asyncio.create_task(monitor.monitor(interval=1, duration=EXPERIMENT_DURATION + 4))
                await asyncio.sleep(2)

                # Iniciar Teste de Carga
                await run_load_test(base_url=LB_URL, rps=rps, duration=EXPERIMENT_DURATION, log_file=log_request_file)

                # Esperar monitoramento terminar
                await asyncio.sleep(2)
                monitor_task.cancel()
                print(f"Cenário {scenario_name} concluído!\n")

if __name__ == "__main__":
    asyncio.run(run_experiment())
