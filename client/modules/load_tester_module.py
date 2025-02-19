import time
import json
import random
import requests

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
        self.total_requests = self.rps * self.duration  # Garante o número correto de requisições

    def send_request(self):
        """Envia uma requisição ao servidor alvo e mede o tempo de resposta."""
        request_start_time = time.time()
        difficulty = random.randint(3, 4)
        
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
        """Executa o teste de carga de forma totalmente síncrona com limitação de RPS."""
        print(f"Iniciando teste de carga: {self.rps} RPS por {self.duration} segundos...")
        time.sleep(random.uniform(0, 0.15))  # Delay inicial aleatório de até 150ms
        start_time = time.time()
        last_request_time = start_time
        
        for _ in range(self.total_requests):
            if time.time() - start_time > self.duration:
                break  # Garante que não exceda a duração máxima
            
            self.send_request()
            
            elapsed_time = time.time() - last_request_time
            if elapsed_time < self.request_interval:
                time.sleep(self.request_interval - elapsed_time)
            last_request_time = time.time()
        
        self.save_logs()
    
    def save_logs(self):
        """Salva os logs no final do teste para evitar I/O frequente."""
        with open(self.log_file, "w") as log:
            for entry in self.results:
                log.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    tester = LoadTester("http://localhost:8080", rps=100, duration=5)
    tester.run()
