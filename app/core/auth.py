# app/core/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, ExpiredSignatureError
import traceback

from app.core.security import verify_jwt_token
from app.log.logging import logger

# from app.models.user import User
# from app.services.user_service import get_user_by_username

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Log token info (not the full token for security)
        if token:
            token_preview = token[:10] + "..." if len(token) > 10 else token
            logger.debug(f"Auth attempt with token prefix: {token_preview}")
        else:
            logger.warning("Auth attempt with empty token")
            
        payload = verify_jwt_token(token)
        user_id: str = payload.get("id")
        
        if user_id is None:
            logger.warning("Token payload missing 'id' field", payload=payload)
            raise credentials_exception
            
        logger.debug(f"Successful authentication for user_id: {user_id}")
        return int(user_id)
        
    except ExpiredSignatureError as e:
        logger.warning(f"Token expired: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning(f"JWT validation error: {str(e)}")
        raise credentials_exception
    except ValueError as e:
        # This might happen if int(user_id) fails
        logger.warning(f"Invalid user_id format: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected auth error: {str(e)}", exc_info=True)
        logger.debug(f"Auth error traceback: {traceback.format_exc()}")
        raise credentials_exception
