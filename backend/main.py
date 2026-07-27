import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import match, parse, share

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
# /s/{id} — 브라우저와 크롤러가 직접 여는 HTML. CORS 와 무관하다
# (fetch 가 아니라 페이지 이동이므로).
app.include_router(share.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "Musiknot API"}
