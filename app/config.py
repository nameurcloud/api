import os
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
IS_DEV = os.getenv("IS_DEV", True)
