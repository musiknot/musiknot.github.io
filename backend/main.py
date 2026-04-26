import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import match, parse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="Musiknot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://musiknot.github.io",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(match.router)
app.include_router(parse.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "Musiknot API"}
