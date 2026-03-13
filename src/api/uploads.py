from fastapi import APIRouter, File, UploadFile, HTTPException
import shutil
import os
import uuid

router = APIRouter(prefix="/api/upload", tags=["Uploads"])

UPLOAD_DIRECTORY = "src/static/uploads"

@router.post("")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

    ext = file.filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

    return {"filename": filename, "path": f"/static/uploads/{filename}"}
