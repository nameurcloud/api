import json
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
from fastapi.middleware.cors import CORSMiddleware
from app.auth import is_valid_delete_path, is_valid_generate_path, is_valid_view_path
from app.config import BACKEND_URL, IS_DEV
from google.auth.transport.requests import Request as GoogleRequest
from google.auth import default
from google.oauth2 import id_token

# ----------------
# Logging setup
# ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI()

# ----------------
# CORS setup
# ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

# ----------------
# Get ID Token for Cloud Run audience
# ----------------
async def get_id_token(audience: str) -> str:
    logger.info(f"Fetching ID token for audience: {audience}")
    credentials, _ = default()
    auth_req = GoogleRequest()
    try:
        token = id_token.fetch_id_token(auth_req, audience)
        logger.info(f"Successfully fetched ID token. Token prefix: {token[:10]}...")
        return token
    except Exception as e:
        logger.exception("Failed to fetch ID token.")
        raise HTTPException(status_code=500, detail=f"Token generation error: {str(e)}")

# ----------------
# API Route Proxy
# ----------------
@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(full_path: str, request: Request):
    logger.info(f"Incoming request: {request.method} /{full_path}")

    # ----------------
    # Validate route
    # ----------------
    if not (
        is_valid_view_path(full_path)
        or is_valid_generate_path(full_path)
        or is_valid_delete_path(full_path)
    ):
        logger.warning(f"Invalid path attempted: {full_path}")
        raise HTTPException(status_code=400, detail="Invalid URL")

    # ----------------
    # Extract API Key
    # ----------------
    api_key = request.headers.get("Authorization")
    logger.debug(f"API key present: {bool(api_key)}")

    # ----------------
    # Prepare payload
    # ----------------
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
            "body": body_json
        }
    else:
        params = {
            "path": full_path,
            "key": api_key,
            "method": request.method
        }

    # ----------------
    # Prepare headers (filter host & content-length)
    # ----------------
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }

    # ----------------
    # Inject ID Token
    # ----------------

    if not IS_DEV:
        print("Production . Generating backend auth token")
        try:
            token = await get_id_token(BACKEND_URL)
            headers["Authorization"] = f"Bearer {token}"
            logger.info(f"ID token injected. Token starts with: {token[:10]}...")
        except Exception as e:
            logger.exception("Failed to generate or inject ID token.")
            raise HTTPException(status_code=500, detail=f"ID token injection failed: {str(e)}")
    else:
        print("Developemt . Not generating backend auth token")
    # ----------------
    # Forward to backend
    # ----------------
    backend_url = f"{BACKEND_URL}/apy/{full_path.split('/')[2]}"
    logger.info(f"Forwarding request to backend: {backend_url}")
    logger.info(params)
    logger.info(headers)
    try:
        async with httpx.AsyncClient() as client:
            backend_response = await client.post(
                url=backend_url,
                headers=headers,
                json=params,
            )
        logger.info(f"Backend responded with status: {backend_response.status_code}")
    except httpx.HTTPError as e:
        logger.exception("Request to backend failed.")
        raise HTTPException(status_code=502, detail=f"Backend request error: {str(e)}")

    # ----------------
    # Parse response
    # ----------------
    try:
        content = backend_response.json()
    except Exception:
        content = backend_response.text

    return JSONResponse(
        status_code=backend_response.status_code,
        content=content if isinstance(content, dict) else {"detail": content},
    )
