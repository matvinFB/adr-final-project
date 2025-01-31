import socket
import json

# Configurações do balanceador
SERVERS = [
    ("192.168.1.2", 8080),  # Servidor 1
    ("192.168.2.2", 8080),  # Servidor 2
]

# Configuração do balanceador
LB_HOST = "0.0.0.0"  # Escuta em todas as interfaces
LB_PORT = 8080       # Porta do balanceador

# Índice para round-robin
server_index = 0


def forward_request(client_socket):
    global server_index

    # Seleciona o servidor baseado no índice atual (round-robin)
    server_addr = SERVERS[server_index]
    server_index = (server_index + 1) % len(SERVERS)  # Atualiza o índice

    try:
        # Recebe a requisição do cliente
        request = client_socket.recv(4096)
        if not request:
            print("[INFO] Requisição vazia recebida, fechando conexão.")
            client_socket.close()
            return

        # Conecta ao servidor escolhido
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.connect(server_addr)
            print(f"[INFO] Encaminhando requisição para {server_addr}.")

            # Envia a requisição para o servidor
            server_socket.sendall(request)

            # Recebe a resposta do servidor
            response = server_socket.recv(4096)

            # Retorna a resposta ao cliente
            client_socket.sendall(response)

    except Exception as e:
        print(f"[ERRO] Falha ao encaminhar requisição: {e}")

    finally:
        client_socket.close()


def start_load_balancer():
    # Cria o socket do balanceador
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as lb_socket:
        lb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lb_socket.bind((LB_HOST, LB_PORT))
        lb_socket.listen(5)
        print(f"[INFO] Load Balancer escutando em {LB_HOST}:{LB_PORT}")

        while True:
            # Aceita conexão do cliente
            client_socket, client_addr = lb_socket.accept()
            print(f"[INFO] Conexão recebida de {client_addr}")

            # Processa a requisição e repassa ao servidor
            forward_request(client_socket)


if __name__ == "__main__":
    start_load_balancer()

