from fastapi import FastAPI, Request
from starlette.responses import Response, JSONResponse
import uvicorn
import httpx

# Lista de servidores, cada um com "host", "port" e "weight".
SERVERS = [
    {"host": "192.168.1.2", "port": 8080, "weight": 1},
    {"host": "192.168.2.2", "port": 8080, "weight": 1},
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

    # Extrai dados da requisição original
    method = request.method
    headers = dict(request.headers)  # Convertendo para dict para facilitar manipulação
    content = await request.body()
    params = dict(request.query_params)  # Query params

    # Remove/ajusta cabeçalhos que não queremos passar diretamente (opcional)
    # Exemplo: se quiser remover 'host', etc., dependendo da sua necessidade.
    headers.pop("host", None)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=content,
                params=params
            )

        # Reconstrói a resposta para retornar ao cliente
        # Filtra cabeçalhos "hop-by-hop" (Transfer-Encoding, Connection, etc.) se necessário
        excluded_headers = {
            "content-length",
            "transfer-encoding",
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "upgrade",
        }

        response_headers = {
            k: v
            for k, v in resp.headers.items()
            if k.lower() not in excluded_headers
        }

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=response_headers
        )
    except httpx.RequestError as e:
        return JSONResponse(
            {"error": f"Failed to connect to upstream server: {e}"},
            status_code=502
        )


def start_load_balancer():
    global servers_weighted_list
    servers_weighted_list = build_weighted_list(SERVERS)
    uvicorn.run(app, host=LB_HOST, port=LB_PORT)


if __name__ == "__main__":
    start_load_balancer()
