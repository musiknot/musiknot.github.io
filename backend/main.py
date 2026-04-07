from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import match, parse

app = FastAPI(title="Musiknot API")

# CORS 설정
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

# 라우터 등록
app.include_router(match.router)
app.include_router(parse.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "Musiknot API"}