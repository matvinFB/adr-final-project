import asyncio
import httpx
import time
import json
import random
from statistics import mean

class LoadTester:
    def __init__(self, base_url, rps=100, duration=10, log_file="load_test.log"):
        """
        :param base_url: URL do load balancer ou servidor alvo
        :param rps: Requisições por segundo desejadas
        :param duration: Duração total do teste em segundos
        :param log_file: Caminho do arquivo de log
        """
        self.base_url = base_url.rstrip('/')
        self.rps = min(rps, 10_000)  # Limite máximo de 10.000 RPS
        self.duration = duration
        self.client = httpx.AsyncClient()
        self.results = []
        self.log_file = log_file

    async def send_request(self):
        """Envia uma requisição ao servidor alvo e mede o tempo de resposta."""
        request_start_time = time.time()
        difficulty = int(max(1000, min(5000, random.gauss(3000, 800))))  # Distribuição normal entre 1000 e 5000
        
        try:
            response = await self.client.post(
                f"{self.base_url}/test",
                json={"difficulty": difficulty}
            )
            request_end_time = time.time()
            latency = request_end_time - request_start_time
            
            response_data = response.json()
            server_start_time = response_data.get("start_time")
            server_end_time = response_data.get("end_time")
            result = response_data.get("result")
            
            log_entry = {
                "request_sent": request_start_time,
                "request_received": request_end_time,
                "server_start": server_start_time,
                "server_end": server_end_time,
                "latency": latency,
                "difficulty": difficulty,
                "result": result,
                "status": response.status_code
            }
            
            with open(self.log_file, "a") as log:
                log.write(json.dumps(log_entry) + "\n")
            
            self.results.append((latency, response.status_code))
        except httpx.RequestError:
            self.results.append((None, 'error'))

    async def run(self):
        """Executa o teste de carga pelo tempo determinado."""
        print(f"Iniciando teste de carga: {self.rps} RPS por {self.duration} segundos...")
        start_time = time.time()
        request_interval = 1 / self.rps

        while time.time() - start_time < self.duration:
            loop_start = time.time()
            
            tasks = []
            for _ in range(self.rps):
                tasks.append(self.send_request())
                await asyncio.sleep(request_interval)  # Distribui as requisições no tempo correto
            
            await asyncio.gather(*tasks)
            
            elapsed = time.time() - loop_start
            remaining_time = max(0, 1 - elapsed)  # Ajusta o tempo para evitar excessos
            await asyncio.sleep(remaining_time)

        await self.client.aclose()
        self.report()

    def report(self):
        """Exibe um relatório básico do teste."""
        latencies = [r[0] for r in self.results if r[0] is not None]
        errors = sum(1 for r in self.results if r[1] == 'error')
        total_requests = len(self.results)
        
        print("\n--- Relatório de Teste ---")
        print(f"Total de requisições: {total_requests}")
        print(f"Erros: {errors} ({(errors / total_requests) * 100:.2f}%)")
        if latencies:
            print(f"Latência média: {mean(latencies):.4f}s")
            print(f"Latência máxima: {max(latencies):.4f}s")
            print(f"Latência mínima: {min(latencies):.4f}s")
        print("---------------------------")

async def run_load_test(base_url, rps=100, duration=10, log_file="load_test.log"):
    """Função para rodar o teste programaticamente."""
    tester = LoadTester(base_url=base_url, rps=rps, duration=duration, log_file=log_file)
    await tester.run()

if __name__ == "__main__":
    asyncio.run(run_load_test("http://localhost:8080", rps=1000, duration=5))
