# main FastAPI file (e.g., main.py)
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
from fastapi.middleware.cors import CORSMiddleware
from app.auth import is_valid_delete_path, is_valid_generate_path, is_valid_view_path
from app.config import BACKEND_URL, IS_DEV
from google.auth.transport.requests import Request as GoogleRequest
from google.auth import default
from google.oauth2 import id_token

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",  # for testing
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Allow POST and OPTIONS
    allow_headers=["Authorization", "Content-Type"],  # Allow these headers
)


async def get_id_token(audience: str) -> str:
    # Only needed in production
    credentials, _ = default()
    auth_req = GoogleRequest()
    target_audience = audience
    return id_token.fetch_id_token(auth_req, target_audience)

@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(full_path: str, request: Request):
    if not (
        is_valid_view_path(full_path)
        or is_valid_generate_path(full_path)
        or is_valid_delete_path(full_path)
    ):
        raise HTTPException(status_code=400, detail="Invalid URL")

    # Get incoming API key, pass it to backend via body (optional)
    api_key = request.headers.get("Authorization")
    if request.method == "POST":
        raw_body = await request.body()
        body_str = raw_body.decode('utf-8') if raw_body else ""
        try:
            body_json = json.loads(body_str)
        except Exception:
            body_json = body_str
        params = {
            "path": full_path,
            "key": api_key,
            "method": request.method,
            "body" :  body_json
        }
    else:
        params = {
            "path": full_path,
            "key": api_key,
            "method": request.method
        }

    headers = {
    k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")
}


    # Inject ID token for backend only in production
    if not IS_DEV:
        try:
            id_token_value = await get_id_token(BACKEND_URL)
            headers["Authorization"] = f"Bearer {id_token_value}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get ID token: {str(e)}")

    async with httpx.AsyncClient() as client:
        backend_response = await client.post(
            url=f"{BACKEND_URL}/apy/{full_path.split('/')[2]}",
            headers=headers,
            json=params,
        )

    try:
        content = backend_response.json()
    except Exception:
        content = backend_response.text

    return JSONResponse(
        status_code=backend_response.status_code,
        content=content if isinstance(content, dict) else {"detail": content},
    )