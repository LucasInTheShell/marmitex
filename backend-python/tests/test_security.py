from app.modules.auth.infrastructure.password import ArgonPasswordService
from app.modules.auth.infrastructure.session import OpaqueSessionService


def test_passwords_are_hashed_and_verified() -> None:
    passwords = ArgonPasswordService()
    password_hash = passwords.hash("uma-senha-segura")

    assert "uma-senha-segura" not in password_hash
    assert passwords.verify(password_hash, "uma-senha-segura")
    assert not passwords.verify(password_hash, "senha-incorreta")


def test_session_token_hash_is_stable_and_does_not_expose_token() -> None:
    sessions = OpaqueSessionService()
    token_hash = sessions.hash("secret-session-token")

    assert token_hash == sessions.hash("secret-session-token")
    assert "secret-session-token" not in token_hash
