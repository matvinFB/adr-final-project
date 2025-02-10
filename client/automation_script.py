import asyncio
import os
import multiprocessing
import shutil
from dotenv import load_dotenv
from modules.proxmox_vm_manager_module import ProxmoxVMManager
from modules.proxmox_monitor_module import ProxmoxMonitor
from modules.load_tester_module import LoadTester

# Carregar variáveis do .env
load_dotenv()

PROXMOX_IP = os.getenv("PROXMOX_IP")
PROXMOX_TOKEN = os.getenv("PROXMOX_TOKEN")
NODE = os.getenv("NODE")
VM_ID_1 = int(os.getenv("VM_ID_1"))  # Servidor 1 (Fixado com 1 núcleo)
VM_ID_2 = int(os.getenv("VM_ID_2"))  # Servidor 2 (Irá variar o número de núcleos)
VM_IP_1 = os.getenv("VM_IP_1")  # IP da VM 1 para checagem de serviço
VM_IP_2 = os.getenv("VM_IP_2")  # IP da VM 2 para checagem de serviço
LB_URL = os.getenv("LB_URL")
SERVER_1_CORES = 1
EXPERIMENT_DURATION = int(os.getenv("EXPERIMENT_DURATION", 30))
MAX_RPS_PER_PROCESS = 100

# Definição dos fatores
RPS_LEVELS = list(map(int, os.getenv("RPS_LEVELS", "100,1000,10000").split(',')))
CORE_LEVELS = list(map(int, os.getenv("CORE_LEVELS", "1,2,4,8").split(',')))
ALGORITHMS = os.getenv("ALGORITHMS", "round_robin,balanced_round_robin").split(',')

def clear_logs():
    """Remove todos os arquivos de log antes de iniciar o experimento."""
    log_dir = "logs"
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)
    os.makedirs(log_dir, exist_ok=True)

def start_monitoring(vm_id, log_file, duration):
    """Inicia o monitoramento em um processo separado."""
    monitor = ProxmoxMonitor(PROXMOX_IP, PROXMOX_TOKEN, NODE, vm_id, log_file)
    monitor.monitor(interval=1//5, duration=duration)

def run_load_test_process(process_num, base_url, rps, duration, scenario_name):
    """Executa o teste de carga em um processo separado."""
    log_request_file = f"logs/{scenario_name}-proc{process_num}-requests.txt"
    tester = LoadTester(base_url=base_url, rps=rps, duration=duration, log_file=log_request_file)
    tester.run()

import requests

async def set_load_balancer_config(algorithm, cores_server2):
    """Atualiza a configuração do Load Balancer"""
    servers_config = [
        {"host": "192.168.1.2", "port": 8080, "weight": SERVER_1_CORES, "id": 1},
        {"host": "192.168.2.2", "port": 8080, "weight": cores_server2, "id": 2}
    ]

    if algorithm == "round_robin":
        servers_config = [{"host": s["host"], "port": s["port"], "weight": 1, "id": s["id"]} for s in servers_config]
    
    try:
        response = requests.post(f"{LB_URL}/admin/config", json={"servers": servers_config}, timeout=10.0)
        response.raise_for_status()
    except requests.RequestException as e:
        error_message = f"Error: {e}, Status Code: {getattr(e.response, 'status_code', 'N/A')}"
        print(error_message)

async def run_experiment():
    clear_logs()  # Limpa todos os logs antes de iniciar o experimento
    previous_cores = None
    vm_manager = ProxmoxVMManager(PROXMOX_IP, PROXMOX_TOKEN, NODE, VM_ID_2, VM_IP_2)
    await asyncio.sleep(5)
    
    for cores in CORE_LEVELS:
        if previous_cores != cores:
            print(f"Alterando núcleos do servidor 2 para {cores}...")
            vm_manager.update_vm_cores(cores)
            previous_cores = cores

        for rps in RPS_LEVELS:
            for algorithm in ALGORITHMS:
                scenario_name = f"rps{rps}-cores{cores}-alg{algorithm}"
                log_monitor_file_1 = f"logs/{scenario_name}-vm1-monitoring.txt"
                log_monitor_file_2 = f"logs/{scenario_name}-vm2-monitoring.txt"
                
                print(f"\n=== Executando cenário: {scenario_name} ===")

                # Configurar Load Balancer
                await set_load_balancer_config(algorithm, cores)

                # Iniciar monitoramento em processos separados
                monitor_process_1 = multiprocessing.Process(target=start_monitoring, args=(VM_ID_1, log_monitor_file_1, EXPERIMENT_DURATION+20))
                monitor_process_2 = multiprocessing.Process(target=start_monitoring, args=(VM_ID_2, log_monitor_file_2, EXPERIMENT_DURATION+20))
                monitor_process_1.start()
                monitor_process_2.start()
                
                await asyncio.sleep(2)  # Aguarda um tempo antes de iniciar as requisições

                # Iniciar Teste de Carga com múltiplos processos
                num_processes = max(1, rps // MAX_RPS_PER_PROCESS)
                processes = []

                for i in range(num_processes):
                    process_rps = min(MAX_RPS_PER_PROCESS, rps - (i * MAX_RPS_PER_PROCESS))
                    p = multiprocessing.Process(target=run_load_test_process, args=(i, LB_URL, process_rps, EXPERIMENT_DURATION, scenario_name))
                    processes.append(p)
                    p.start()
                
                for p in processes:
                    p.join()

                # Esperar monitoramento terminar
                monitor_process_1.join()
                monitor_process_2.join()
                print(f"Cenário {scenario_name} concluído!\n")

if __name__ == "__main__":
    asyncio.run(run_experiment())
