#!/usr/bin/env python3

import http.server
import socketserver
import os
import json
import time
import hashlib
import socket
from concurrent.futures import ProcessPoolExecutor

# Get the hostname and IP of the server
HOSTNAME = socket.gethostname()
IP_ADDRESS = socket.gethostbyname(HOSTNAME)

# Descobrindo quantidade de núcleos disponível
NUM_CORES = os.cpu_count()

# Cria um pool de processos global
pool = ProcessPoolExecutor(max_workers=NUM_CORES)

def do_hashing(difficulty: int) -> str:
    """
    Executa 'difficulty' rodadas de hashing de uma string fixa.
    Retorna o hash final como string em hexadecimal.
    """
    data = b"Hello, World!"
    current_hash = data

    for _ in range(difficulty):
        # Calcula o hash do valor atual
        current_hash = hashlib.sha512(current_hash).digest()

    # Converte o hash final para hexadecimal
    return current_hash.hex()


class MultiCoreRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    Handler responsável por receber requisições POST contendo JSON:
      { "difficulty": <int> }

    Responde com JSON:
      {
        "start_time": <timestamp>,
        "end_time": <timestamp>,
        "result": <hash_final>
      }
    """

    def do_POST(self):
        # Lê o conteúdo do POST
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        # Parse do JSON recebido
        try:
            data = json.loads(post_data)
            difficulty = data.get("difficulty", 1)
        except (json.JSONDecodeError, TypeError):
            self.send_error(400, "JSON inválido ou ausência de campo 'difficulty'")
            return

        # Marca o início da tarefa
        start_time = time.time()

        # Envia a tarefa para o Pool de Processos
        future = pool.submit(do_hashing, difficulty)

        # Aguarda o resultado
        result = future.result()

        # Marca o fim da tarefa
        end_time = time.time()

        # Monta o JSON de resposta
        response = {
                "start_time": start_time,
                "end_time": end_time,
                "result": result,
                "server": HOSTNAME
            }
        response_json = json.dumps(response)

        # Envia resposta
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response_json.encode("utf-8"))


def run_server(port=8080):
    """
    Inicia o servidor em todas as interfaces (0.0.0.0) na porta especificada.
    """
    with socketserver.TCPServer(("0.0.0.0", port), MultiCoreRequestHandler) as httpd:
        print(f"Servidor ouvindo em http://0.0.0.0:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Encerrando servidor...")
        finally:
            httpd.server_close()


if __name__ == "__main__":
    run_server(port=8080)

