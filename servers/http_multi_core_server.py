#!/usr/bin/env python3
import asyncio
import time
import hashlib
import os
import socket
from concurrent.futures import ProcessPoolExecutor

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Setup FastAPI and the process pool
app = FastAPI()
NUM_CORES = os.cpu_count()
pool = ProcessPoolExecutor(max_workers=NUM_CORES)

# Data model for the request
class HashRequest(BaseModel):
    difficulty: int

# CPU-bound proof-of-work function
def do_hashing(difficulty: int) -> str:
    """
    Performs a proof-of-work style hash computation.
    
    Instead of a fixed number of hash iterations, this function finds a nonce such that
    the SHA-512 hash of (data + nonce) starts with a number of zeros equal to the difficulty.
    Increasing difficulty exponentially increases the CPU work required.
    """
    data = b"Hello, World!"
    nonce = 0
    target_prefix = "0" * difficulty  # e.g., if difficulty == 4, target_prefix = "0000"
    
    while True:
        # Convert nonce to bytes and combine with data
        combined = data + str(nonce).encode()
        # Compute the SHA-512 hash
        hash_result = hashlib.sha512(combined).hexdigest()
        # Check if the hash meets the difficulty (i.e., has the required number of leading zeros)
        if hash_result.startswith(target_prefix):
            # Return both the nonce and the resulting hash for verification
            return f"Nonce: {nonce}, Hash: {hash_result}"
        nonce += 1

# Asynchronous endpoint that offloads the CPU-bound task to the process pool
@app.post("/hash")
async def hash_endpoint(request: HashRequest):
    start_time = time.time()
    loop = asyncio.get_running_loop()
    # Offload CPU-bound task to the process pool
    try:
        result = await loop.run_in_executor(pool, do_hashing, request.difficulty)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    end_time = time.time()
    hostname = socket.gethostname()
    return {
        "start_time": start_time,
        "end_time": end_time,
        "result": result,
        "server": hostname
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("http_multi_core_server:app", host="0.0.0.0", port=8080, log_level="info", workers=NUM_CORES)