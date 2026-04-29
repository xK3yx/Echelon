from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.limiter import limiter
from app.routers import admin, analyze, careers, courses, export, health, profiles, recommendations, resume

app = FastAPI(
    title="Echelon v2.2",
    description="AI-assisted career intelligence API",
    version="2.2.0",
)

# Rate-limiter state (used by @limiter.limit() decorators in routers)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_origins = ["http://localhost:3000"]
if settings.public_base_url:
    _cors_origins.append(settings.public_base_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_HTTP_CODE_MAP: dict[int, str] = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_ERROR",
}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException) -> JSONResponse:
    # Some routers (e.g. resume) raise HTTPException with a pre-structured dict
    # containing "code" already set — pass it through verbatim.
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
        )
    code = _HTTP_CODE_MAP.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": str(exc.detail), "details": {}}},
    )


def _safe_errors(exc: RequestValidationError) -> list:
    # Pydantic v2 model_validator errors can place exception objects in ctx,
    # which aren't JSON-serializable. Convert anything non-primitive to str.
    def _sanitize(obj):
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(i) for i in obj]
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        return str(obj)

    return _sanitize(exc.errors())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": _safe_errors(exc)},
            }
        },
    )


app.include_router(health.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(careers.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(resume.router, prefix="/api")
app.include_router(courses.router, prefix="/api")
app.include_router(export.router, prefix="/api")
