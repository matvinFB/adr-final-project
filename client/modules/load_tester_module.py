import time
import json
import random
import requests
import threading

class LoadTester:
    def __init__(self, base_url, rps=100, duration=10, log_file="load_test.log"):
        """
        :param base_url: URL do load balancer ou servidor alvo
        :param rps: Requisições por segundo desejadas (máx 100 RPS)
        :param duration: Duração total do teste em segundos
        :param log_file: Caminho do arquivo de log
        """
        self.base_url = base_url.rstrip('/')
        self.rps = min(rps, 100)  # Cap máximo de 100 RPS
        self.duration = duration
        self.log_file = log_file
        self.results = []
        self.request_interval = 1 / self.rps
        self.threads = []
        self.lock = threading.Lock()
        self.total_requests = self.rps * self.duration  # Garante o número correto de requisições

    def send_request(self):
        """Envia uma requisição ao servidor alvo e mede o tempo de resposta."""
        request_start_time = time.time()
        difficulty = int(random.gauss(3, 1))
        difficulty = max(1, min(6, difficulty))
        
        try:
            response = requests.post(
                f"{self.base_url}/hash",
                json={"difficulty": difficulty},
                timeout=5.0
            )
            request_end_time = time.time()
            latency = request_end_time - request_start_time
            
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"error": "Invalid JSON response"}

            latency_on_server = response_data.get("end_time", 0) - response_data.get("start_time", 0)
            
            with self.lock:
                self.results.append({
                    "request_sent": request_start_time,
                    "request_received": request_end_time,
                    "latency": latency,
                    "latency_on_server": latency_on_server,
                    "difficulty": difficulty,
                    "status": response.status_code,
                    "server": response_data.get("server")
                })
        except requests.RequestException as e:
            with self.lock:
                self.results.append({"error": str(e)})
    
    def worker(self, requests_per_thread):
        """Thread worker que envia um número fixo de requisições."""
        for _ in range(requests_per_thread):
            self.send_request()
            time.sleep(1/(min(self.rps/5, 100)))  # Mantém as requisições espaçadas corretamente
    
    def run(self):
        """Executa o teste de carga usando múltiplas threads para chamadas não bloqueantes."""
        print(f"Iniciando teste de carga: {self.rps} RPS por {self.duration} segundos...")
        num_threads = min(self.rps//5, 100)
        requests_per_thread = self.total_requests // num_threads
        remainder_requests = self.total_requests % num_threads
        
        for i in range(num_threads):
            extra_request = 1 if i < remainder_requests else 0
            t = threading.Thread(target=self.worker, args=(requests_per_thread + extra_request,))
            self.threads.append(t)
            t.start()
        
        for t in self.threads:
            t.join()
        
        self.save_logs()
    
    def save_logs(self):
        """Salva os logs no final do teste para evitar I/O frequente."""
        with open(self.log_file, "w") as log:
            for entry in self.results:
                log.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    tester = LoadTester("http://localhost:8080", rps=100, duration=5)
    tester.run()
