from fastapi import FastAPI

app = FastAPI(
    title="Kubereats Backend",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"message": "Kubereats backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
