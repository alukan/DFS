from fastapi import FastAPI
import os
import uvicorn
from app.controllers import file_operations, name_mappings, chunk_operations

app = FastAPI()

app.include_router(file_operations.router)
app.include_router(name_mappings.router)
app.include_router(chunk_operations.router)

# Run the user FastAPI app on the specified port
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
