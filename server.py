from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from routers.router import router
from logging_utils import init_request_logging
import uvicorn
import os

app = FastAPI(
    title="Category & Budget Service",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": True},
)

def get_allowed_origins():
    env_origins = os.getenv("CORS_ORIGINS")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",")]

    common_ports = [3000, 3001, 5173, 5174, 8080, 8081]
    return [
        f"http://{host}:{port}"
        for host in ["localhost", "127.0.0.1"]
        for port in common_ports
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_request_logging(app, "soa-category-budget")
app.include_router(router)

def custom_openapi():
    """
    Inject HTTP Bearer auth scheme so Swagger shows the Authorize button for JWT.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )

    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    for path in openapi_schema.get("paths", {}).values():
        for operation in path.values():
            # Apply bearer security to all operations
            operation.setdefault("security", [{"BearerAuth": []}])

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
