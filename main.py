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
logger = logging.getLogger(__name__)

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


async def get_id_token(audience: str) -> str:
    """Get an ID token for the target audience (backend URL)."""
    logger.info(f"Fetching ID token for audience: {audience}")
    credentials, _ = default()
    auth_req = GoogleRequest()
    token = id_token.fetch_id_token(auth_req, audience)
    logger.info("Successfully fetched ID token.")
    return token


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(full_path: str, request: Request):
    logger.info(f"Incoming request: {request.method} /{full_path}")

    # Validate path
    if not (
        is_valid_view_path(full_path)
        or is_valid_generate_path(full_path)
        or is_valid_delete_path(full_path)
    ):
        logger.warning(f"Rejected invalid path: {full_path}")
        raise HTTPException(status_code=400, detail="Invalid URL")

    # Extract Authorization header
    api_key = request.headers.get("Authorization")
    logger.debug(f"Authorization header received: {bool(api_key)}")

    # Prepare request payload
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

    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }

    # Inject Bearer token for backend
    if not IS_DEV:
        try:
            token = await get_id_token(BACKEND_URL)
            headers["Authorization"] = f"Bearer {token}"
        except Exception as e:
            logger.exception("Error generating ID token")
            raise HTTPException(status_code=500, detail=f"Failed to get ID token: {str(e)}")

    backend_url = f"{BACKEND_URL}/apy/{full_path.split('/')[2]}"
    logger.info(f"Forwarding request to backend: {backend_url}")

    try:
        async with httpx.AsyncClient() as client:
            backend_response = await client.post(
                url=backend_url,
                headers=headers,
                json=params,
            )
        logger.info(f"Backend responded with status: {backend_response.status_code}")
    except httpx.HTTPError as e:
        logger.exception("Request to backend failed")
        raise HTTPException(status_code=502, detail=f"Request to backend failed: {str(e)}")

    try:
        content = backend_response.json()
    except Exception:
        content = backend_response.text

    return JSONResponse(
        status_code=backend_response.status_code,
        content=content if isinstance(content, dict) else {"detail": content},
    )
