from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import admin, analyze, careers, health, profiles, recommendations

app = FastAPI(
    title="Echelon v2.1",
    description="AI-assisted career intelligence API",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
