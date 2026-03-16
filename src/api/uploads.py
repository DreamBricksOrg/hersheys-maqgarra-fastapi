from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import shutil
import os
import uuid
import logging
from util import document_scanner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/upload", tags=["Uploads"])

UPLOAD_DIRECTORY = "src/static/uploads"

@router.post("")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

@router.post("/process")
async def process_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

    ext = file.filename.split('.')[-1]
    base_id = uuid.uuid4().hex
    
    orig_filename = f"{base_id}_orig.{ext}"
    proc_filename = f"{base_id}_proc.{ext}"
    
    orig_path = os.path.join(UPLOAD_DIRECTORY, orig_filename)
    proc_path = os.path.join(UPLOAD_DIRECTORY, proc_filename)

    try:
        # Save original
        with open(orig_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Process image
        document_scanner.process_receipt(orig_path, proc_path)
        
    except Exception as e:
        logger.error("Failed to process image: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

    return {
        "original_path": f"/static/uploads/{orig_filename}", 
        "original_cdn": f"/api/upload/cdn/{orig_filename}",
        "processed_path": f"/static/uploads/{proc_filename}",
        "processed_cdn": f"/api/upload/cdn/{proc_filename}"
    }

    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

    ext = file.filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

    return {"filename": filename, "path": f"/static/uploads/{filename}", "cdn": f"/api/upload/cdn/{filename}"}


@router.api_route("/cdn/{filename}", methods=["GET", "HEAD"])
async def serve_image(filename: str):
    """Serve imagem com Content-Type correto (image/jpeg, image/png, etc)."""
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Image not found")

    ext = filename.rsplit(".", 1)[-1].lower()
    media_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "pdf": "application/pdf"}
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(file_path, media_type=media_type)
