from fastapi import Header, HTTPException
from app.config import get_settings


async def verify_api_key(x_api_key: str = Header(default=None)):
    settings = get_settings()
    
    if not settings.api_secret_key:
        return  # no key configured, skip auth (local dev)
    
    if x_api_key != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")