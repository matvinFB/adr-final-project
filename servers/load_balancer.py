from fastapi import FastAPI, Request
from starlette.responses import Response, JSONResponse
import uvicorn
import httpx

# Lista de servidores, cada um com "host", "port" e "weight".
SERVERS = [
    {"host": "192.168.1.2", "port": 8080, "weight": 1, "id": 1},
    {"host": "192.168.2.2", "port": 8080, "weight": 1, "id": 2},
]

LB_HOST = "0.0.0.0"
LB_PORT = 8080

servers_weighted_list = []
server_index = 0

app = FastAPI()


def build_weighted_list(servers):
    expanded = []
    for srv in servers:
        weight = srv.get("weight", 1)
        expanded.extend([srv] * weight)
    return expanded


def get_next_server():
    global server_index
    if not servers_weighted_list:
        return None
    server = servers_weighted_list[server_index]
    server_index = (server_index + 1) % len(servers_weighted_list)
    return server


@app.get("/admin/config")
def get_config():
    return {"servers": SERVERS}


@app.post("/admin/config")
def update_config(config_data: dict):
    global SERVERS, servers_weighted_list, server_index

    if "servers" in config_data:
        SERVERS = config_data["servers"]

    servers_weighted_list = build_weighted_list(SERVERS)
    server_index = 0

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

    # Captura erro de desconexão do cliente
    try:
        content = await request.body()
    except starlette.requests.ClientDisconnect:
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
    global servers_weighted_list
    servers_weighted_list = build_weighted_list(SERVERS)
    uvicorn.run(app, host=LB_HOST, port=LB_PORT)


if __name__ == "__main__":
    start_load_balancer()
