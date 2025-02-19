import time
import json
import random
import requests
import threading

class LoadTester:
    def __init__(self, base_url, duration=10, log_file="load_test.log", max_rps=1):
        """
        :param base_url: URL do load balancer ou servidor alvo
        :param duration: Duração total do teste em segundos
        :param log_file: Caminho do arquivo de log
        :param max_rps: Limite máximo de requisições por segundo
        """
        self.base_url = base_url.rstrip('/')
        self.duration = duration
        self.log_file = log_file
        self.max_rps = max_rps
        self.results = []
        self.stop_time = time.time() + self.duration
        self.last_request_time = 0
        self.lock = threading.Lock()

    def send_request(self):
        """Envia uma requisição ao servidor alvo e mede o tempo de resposta, respeitando o limite de RPS."""
        while time.time() < self.stop_time:
            with self.lock:
                current_time = time.time()
                elapsed_time = current_time - self.last_request_time
                if elapsed_time < 0.9:
                    time.sleep(0.99-elapsed_time)
                self.last_request_time = time.time()
            
            request_start_time = time.time()
            difficulty = random.gauss(3, 1.5)
            
            try:
                response = requests.post(f"{self.base_url}/hash", json={"difficulty": difficulty}, timeout=5)
                request_end_time = time.time()
                latency = (request_end_time - request_start_time) * 1000  # Convertendo para ms
                
                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    response_data = {"error": "Invalid JSON response"}
                
                latency_on_server = (response_data.get("end_time", 0) - response_data.get("start_time", 0)) * 1000  # Convertendo para ms
                
                self.results.append({
                    "request_sent": request_start_time,
                    "request_received": request_end_time,
                    "latency": latency,
                    "latency_on_server": latency_on_server,
                    "difficulty": difficulty,
                    "status": response.status_code,
                    "server": response_data.get("server")
                })
            except Exception as e:
                self.results.append({"error": str(e)})
    
    def run(self):
        """Executa o teste de carga respeitando o limite de RPS."""
        print(f"Iniciando teste de carga com limite de {self.max_rps*10} RPS por {self.duration} segundos...")
        threads = []
        for _ in range(10):  # Criar múltiplas threads para distribuir carga
            t = threading.Thread(target=self.send_request)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        self.save_logs()
    
    def save_logs(self):
        """Salva os logs no final do teste para evitar I/O frequente."""
        with open(self.log_file, "w") as log:
            for entry in self.results:
                log.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    tester = LoadTester("http://localhost:8080", duration=5, max_rps=1)
    tester.run()
