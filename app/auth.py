def validate_key(key: str) -> bool:
    # Replace with real DB/cache/API call
    return key == "Bearer test-api-key"

def check_permission(key: str, path: str, method: str) -> bool:
    # Implement logic per key/role/path/method
    return True  # Allow all for now
