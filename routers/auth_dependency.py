from fastapi import HTTPException, status, Header
from typing import Optional
from services.jwt_service import JWTService

jwt_service = JWTService()

async def verify_jwt_token(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> dict:
    """
    FastAPI dependency that verifies JWT token from Authorization header.
    
    Expected header format: "Bearer <token>"
    
    Returns:
        Dictionary with user information (user_id, username) from token payload
        
    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    
    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>"
        )
    
    token = parts[1]
    
    # Verify token
    payload = jwt_service.verify_token(token, token_type="access")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Extract user information
    user_id = payload.get("sub")
    username = payload.get("username")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID"
        )
    
    return {
        "user_id": user_id,
        "username": username
    }

