# app/auth.py
import re



def is_valid_view_path(path: str) -> bool:
    pattern = r"^name/([a-z0-9]+)/view$"
    return re.match(pattern, path) is not None

def is_valid_generate_path(path: str) -> bool:
    pattern = r"^name/([a-z0-9]+)/generate$"
    return re.match(pattern, path) is not None

def is_valid_delete_path(path: str) -> bool:
    pattern = r"^name/([a-z0-9]+)/delete$"
    return re.match(pattern, path) is not None