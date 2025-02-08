import requests
import time

class ProxmoxVMManager:
    def __init__(self, ip, token, node, vm_id):
        """
        :param ip: Endereço IP do servidor Proxmox
        :param token: Token da API do Proxmox no formato 'USER@REALM!TOKEN_NAME=TOKEN_VALUE'
        :param node: Nome do nó Proxmox onde a VM está localizada
        :param vm_id: ID da VM a ser modificada
        """
        self.proxmox_url = f"https://{ip}:8006"
        self.headers = {"Authorization": f"PVEAPIToken={token}"}
        self.node = node
        self.vm_id = vm_id

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
        """Inicia a VM."""
        url = f"{self.proxmox_url}/api2/json/nodes/{self.node}/qemu/{self.vm_id}/status/start"
        response = requests.post(url, headers=self.headers, verify=False)
        return response.status_code == 200

    def update_vm_cores(self, cores):
        """Executa o fluxo completo: parar VM, atualizar núcleos e iniciar novamente."""
        print(f"Parando VM {self.vm_id}...")
        if self.stop_vm():
            print("VM parada com sucesso. Atualizando núcleos...")
            if self.set_cpu_cores(cores):
                print("Configuração de núcleos alterada. Iniciando VM...")
                if self.start_vm():
                    print("VM iniciada com sucesso!")
                    return True
                else:
                    print("Erro ao iniciar a VM.")
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
        vm_id=100
    )
    
    manager.update_vm_cores(4)
