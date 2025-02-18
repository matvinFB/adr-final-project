from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
import uvicorn
import httpx
import redis
import json

# Configuração do Redis
redis_client = redis.Redis(host="localhost", port=6379, db=0)

# Lista de servidores, cada um com "host", "port", "weight" e "id".
SERVERS = [
    {"host": "192.168.1.2", "port": 8080, "weight": 1, "id": 1},
    {"host": "192.168.2.2", "port": 8080, "weight": 1, "id": 2},
]

LB_HOST = "0.0.0.0"
LB_PORT = 8080

# Gerar uma lista expandida de servidores baseada no peso
def build_weighted_list(servers):
    expanded = []
    for srv in servers:
        weight = srv.get("weight", 1)
        expanded.extend([srv] * weight)
    return expanded

servers_weighted_list = build_weighted_list(SERVERS)

app = FastAPI()


def get_next_server():
    if not servers_weighted_list:
        return None
    # Incrementa de forma atômica o contador no Redis.
    index = redis_client.incr("server_index") - 1
    # Se o índice ficar muito alto, opcionalmente podemos resetá-lo.
    total_servers = len(servers_weighted_list)
    index = index % total_servers
    return servers_weighted_list[index]


@app.get("/admin/config")
def get_config():
    return {"servers": SERVERS}


@app.post("/admin/config")
def update_config(config_data: dict):
    global SERVERS, servers_weighted_list

    if "servers" in config_data:
        SERVERS = config_data["servers"]

    servers_weighted_list = build_weighted_list(SERVERS)
    # Opcional: reseta o contador no Redis quando a configuração é atualizada.
    redis_client.set("server_index", 0)
    return {"status": "config_updated", "servers": SERVERS}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_request(request: Request, path: str):
    server = get_next_server()
    if not server:
        return JSONResponse({"error": "No servers configured"}, status_code=503)

    target_url = f"http://{server['host']}:{server['port']}/{path}"
    method = request.method
    headers = dict(request.headers)
    params = dict(request.query_params)

    headers.pop("host", None)

    try:
        content = await request.body()
    except Exception as e:
        return JSONResponse({"error": "Client disconnected before sending body"}, status_code=400)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=content,
                params=params
            )

        try:
            response_data = response.json()
        except json.JSONDecodeError:
            response_data = {"error": "Invalid JSON response from server"}

        response_data["server_id"] = server["id"]
        return JSONResponse(content=response_data, status_code=response.status_code)

    except httpx.RequestError as e:
        return JSONResponse(
            {"error": f"Failed to connect to upstream server: {e}", "server_id": server["id"]},
            status_code=502
        )


def start_load_balancer():
    uvicorn.run(app, host=LB_HOST, port=LB_PORT)


if __name__ == "__main__":
    start_load_balancer()
