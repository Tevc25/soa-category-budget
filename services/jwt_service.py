import jwt
import os
from typing import Dict, Optional

class JWTService:
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"

    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict]:
        """
        Verifies a JWT token and returns the payload if valid.
        
        Args:
            token: The JWT token string
            token_type: Expected token type ("access" or "refresh")
            
        Returns:
            Dictionary with token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verify token type matches
            if payload.get("type") != token_type:
                return None
                
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

