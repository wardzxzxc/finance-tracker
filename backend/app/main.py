from fastapi import FastAPI

from app.api.transactions import router as transactions_router

app = FastAPI(title="Finance Tracker")

app.include_router(transactions_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
