from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.router import router
import uvicorn
import os

app = FastAPI()

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

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)