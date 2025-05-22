import os
from dotenv import load_dotenv

env_name = os.getenv("ENV", "development")
load_dotenv(dotenv_path=f".env.{env_name}")

ENV = os.getenv("ENV", "development")
IS_DEV = ENV == "development"
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

JWT_SECRET = os.getenv("JWT_SECRET", "l5-3tKsfg3y_983!hasjsg@xzd")
