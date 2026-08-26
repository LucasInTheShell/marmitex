from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


def bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if not credentials or credentials.scheme.lower() != "bearer":
        return None
    return credentials.credentials
