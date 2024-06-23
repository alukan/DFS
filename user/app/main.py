from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Path, Query
from typing import List
import hashlib
import requests
import os

app = FastAPI()

# Define the leader URL
LEADER_URL = "http://localhost:8000"

def chunk_file(file_path, chunk_size=1024):
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            yield chunk

def hash_chunk(chunk):
    return hashlib.md5(chunk).hexdigest()

@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...), name: str = Form(...), path: str = Form(...)):
    file_location = f"/tmp/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(file.file.read())
    
    chunk_hashes = []
    for chunk in chunk_file(file_location):
        chunk_hash = hash_chunk(chunk)
        chunk_hashes.append(chunk_hash)
    
    # Construct the full path
    full_path = os.path.join(path, name)
    
    # Send chunk hashes to the leader
    name_mapping = {"full_path": full_path, "chunk_hashes": chunk_hashes}
    response = requests.post(f"{LEADER_URL}/namemappings/", json=name_mapping)
    
    if response.status_code == 200:
        os.remove(file_location)  # Cleanup the temporary file
        return {"message": "File uploaded and processed successfully"}
    else:
        os.remove(file_location)  # Cleanup the temporary file
        raise HTTPException(status_code=response.status_code, detail=response.json().get("detail"))

@app.get("/namemappings/{full_path:path}", response_model=dict)
async def get_name_mapping(full_path: str):
    response = requests.get(f"{LEADER_URL}/namemappings/{full_path}")
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json().get("detail"))

@app.delete("/namemappings/{full_path:path}")
async def delete_name_mapping(full_path: str):
    response = requests.delete(f"{LEADER_URL}/namemappings/{full_path}")
    if response.status_code == 200:
        return {"message": "Name deleted successfully"}
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json().get("detail"))

@app.put("/namemappings/")
async def rename_name_mapping(
    old_path: str = Query(..., description="The current full path of the name mapping"),
    new_path: str = Query(..., description="The new full path of the name mapping")
):
    params = {'old_path': old_path, 'new_path': new_path}
    response = requests.put(f"{LEADER_URL}/namemappings/", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json().get("detail"))

@app.get("/listfiles/", response_model=List[dict])
async def list_files_in_folder(folder_path: str = Query(..., description="The path of the folder to list files from")):
    params = {'folder_path': folder_path}
    response = requests.get(f"{LEADER_URL}/listfiles/", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json().get("detail"))

# Run the user FastAPI app on a different port
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
