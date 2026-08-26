from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.exceptions import ApplicationError
from app.core.logging import configure_logging, request_log_middleware


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    configure_logging()
    app_settings = settings or get_settings()
    app_database = database or Database(app_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await app_database.open()
        try:
            yield
        finally:
            await app_database.close()

    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)
    app.state.settings = app_settings
    app.state.database = app_database
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.middleware("http")(request_log_middleware)

    @app.exception_handler(ApplicationError)
    async def application_error(_: Request, error: ApplicationError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(
        _: Request, __: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_request",
                    "message": "Revise os dados enviados.",
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, error: StarletteHTTPException) -> JSONResponse:
        messages = {
            404: ("not_found", "Recurso não encontrado."),
            405: ("method_not_allowed", "Método não permitido."),
        }
        code, message = messages.get(
            error.status_code, ("http_error", "Não foi possível concluir a solicitação.")
        )
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": code, "message": message}},
            headers=error.headers,
        )

    @app.get("/health", response_model=None, tags=["health"])
    async def health() -> dict[str, str] | JSONResponse:
        try:
            await app_database.healthcheck()
        except Exception:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "database": "unavailable"},
            )
        return {"status": "ok", "database": "ok"}

    app.include_router(api_router)
    return app


app = create_app()
