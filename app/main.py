from fastapi import FastAPI, Request, HTTPException
import httpx
from app.auth import validate_key, check_permission
from app.config import BACKEND_URL

app = FastAPI()

@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(full_path: str, request: Request):
    api_key = request.headers.get("Authorization")
    if not api_key or not validate_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    if not check_permission(api_key, full_path, request.method):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Forward request
    async with httpx.AsyncClient() as client:
        backend_response = await client.request(
            method=request.method,
            url=f"{BACKEND_URL}/{full_path}",
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            content=await request.body()
        )
    return backend_response
