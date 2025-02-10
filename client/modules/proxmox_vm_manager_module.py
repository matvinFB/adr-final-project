import requests
import time
import urllib3

class ProxmoxVMManager:
    def __init__(self, ip, token, node, vm_id, vm_service_ip):
        """
        :param ip: Endereço IP do servidor Proxmox
        :param token: Token da API do Proxmox no formato 'USER@REALM!TOKEN_NAME=TOKEN_VALUE'
        :param node: Nome do nó Proxmox onde a VM está localizada
        :param vm_id: ID da VM a ser modificada
        :param vm_service_ip: Endereço IP da VM para verificar o serviço via API
        """
        self.proxmox_url = f"https://{ip}:8006"
        self.headers = {"Authorization": f"PVEAPIToken={token}"}
        self.node = node
        self.vm_id = vm_id
        self.vm_service_ip = vm_service_ip
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def stop_vm(self):
        """Para a VM."""
        url = f"{self.proxmox_url}/api2/json/nodes/{self.node}/qemu/{self.vm_id}/status/stop"
        response = requests.post(url, headers=self.headers, verify=False)
        return response.status_code == 200

    def set_cpu_cores(self, cores):
        """Altera a quantidade de núcleos da VM."""
        url = f"{self.proxmox_url}/api2/json/nodes/{self.node}/qemu/{self.vm_id}/config"
        data = {"cores": cores}
        response = requests.put(url, headers=self.headers, json=data, verify=False)
        return response.status_code == 200

    def start_vm(self):
        """Inicia a VM e aguarda até que esteja operacional."""
        url = f"{self.proxmox_url}/api2/json/nodes/{self.node}/qemu/{self.vm_id}/status/start"
        response = requests.post(url, headers=self.headers, verify=False)
        if response.status_code == 200:
            return self.wait_for_vm_service()
        return False

    def wait_for_vm_service(self, timeout=90, interval=5):
        """Aguarda até que a API da VM retorne que o serviço está ativo."""
        url = f"http://{self.vm_service_ip}:8000/status"
        start_time = time.time()
        print(f"Aguardando serviço na VM {self.vm_id} estar operacional...")
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5, verify=False)
                if response.status_code == 200 and response.json().get("service") == "running":
                    print(f"✔ Serviço da VM {self.vm_id} está ativo.")
                    return True
            except requests.RequestException:
                print("VM 2 - Ainda não respondeu") 
                pass
            time.sleep(interval)
        
        print(f"⚠ Timeout ao aguardar o serviço na VM {self.vm_id} iniciar.")
        return False

    def update_vm_cores(self, cores):
        """Executa o fluxo completo: parar VM, atualizar núcleos e iniciar novamente."""
        print(f"Parando VM {self.vm_id}...")
        if self.stop_vm():
            print("VM parada com sucesso. Atualizando núcleos...")
            if self.set_cpu_cores(cores):
                print("Configuração de núcleos alterada. Iniciando VM...")
                if self.start_vm():
                    print("VM iniciada com sucesso e serviço operacional!")
                    return True
                else:
                    print("Erro ao iniciar a VM ou serviço não operacional.")
            else:
                print("Erro ao alterar a configuração de núcleos.")
        else:
            print("Erro ao parar a VM.")
        return False

if __name__ == "__main__":
    manager = ProxmoxVMManager(
        ip="192.168.1.100",
        token="USER@REALM!TOKEN_NAME=TOKEN_VALUE",
        node="pve",
        vm_id=100,
        vm_service_ip="192.168.1.101"
    )
    
    manager.update_vm_cores(4)
