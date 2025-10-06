from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok", "system": "Server is running!"}


@app.get("/")
def read_root():
    return {"Hello": "from FastAPI"}
