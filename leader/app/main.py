from fastapi import FastAPI
import uvicorn
from app.controllers import chunk_server, name_mappings, file_operations

app = FastAPI()

app.include_router(chunk_server.router)
app.include_router(name_mappings.router)
app.include_router(file_operations.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
