from sanic import Sanic, response
from sanic.request import Request
import httpx
import json

app = Sanic("LoadBalancer")

# Lista de servidores, cada um com "host", "port", "weight" e "id".
SERVERS = [
    {"host": "192.168.1.2", "port": 8080, "weight": 1, "id": 1},
    {"host": "192.168.2.2", "port": 8080, "weight": 1, "id": 2},
]

server_index = 0

def build_weighted_list(servers):
    expanded = []
    for srv in servers:
        weight = srv.get("weight", 1)
        expanded.extend([srv] * weight)
    return expanded

servers_weighted_list = build_weighted_list(SERVERS)

def get_next_server():
    global server_index, servers_weighted_list
    if not servers_weighted_list:
        return None
    server = servers_weighted_list[server_index]
    server_index = (server_index + 1) % len(servers_weighted_list)
    return server

@app.route("/admin/config", methods=["GET"])
async def get_config(request: Request):
    return response.json({"servers": SERVERS})

@app.route("/admin/config", methods=["POST"])
async def update_config(request: Request):
    global SERVERS, servers_weighted_list, server_index
    config_data = request.json
    if "servers" in config_data:
        SERVERS = config_data["servers"]

    servers_weighted_list = build_weighted_list(SERVERS)
    server_index = 0

    return response.json({"status": "config_updated", "servers": SERVERS})

@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_request(request: Request, path: str):
    server = get_next_server()
    if not server:
        return response.json({"error": "No servers configured"}, status=503)

    target_url = f"http://{server['host']}:{server['port']}/{path}"
    method = request.method

    # Copy headers and remove 'host'
    headers = dict(request.headers)
    headers.pop("host", None)

    # Convert Sanic request.args to a standard dict
    params = dict(request.args)

    # Request body
    content = request.body

    try:
        async with httpx.AsyncClient() as client:
            upstream_response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                params=params,
                content=content,
            )
    except httpx.RequestError as e:
        return response.json(
            {"error": f"Failed to connect to upstream server: {e}", "server_id": server["id"]},
            status=502,
        )

    try:
        response_data = upstream_response.json()
    except json.JSONDecodeError:
        response_data = {"error": "Invalid JSON response from server"}

    response_data["server_id"] = server["id"]
    return response.json(response_data, status=upstream_response.status_code)


# Para capturar a rota raiz "/"
@app.route("/", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def root_proxy(request: Request):
    return await proxy_request(request, path="")

if __name__ == "__main__":
    # Rodando com um único worker
    app.run(host="0.0.0.0", port=8080, workers=1)
