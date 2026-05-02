from fastapi import FastAPI, UploadFile, File
from app.ocr_reader import read_player_image_from_bytes

app = FastAPI(title="OCR BFV Players")


@app.get("/")
def home():
    return {
        "ok": True,
        "message": "OCR BFV Players API online",
        "endpoint": "POST /ocr",
    }


@app.post("/ocr")
async def ocr_image(file: UploadFile = File(...)):
    content = await file.read()

    result = read_player_image_from_bytes(
        content,
        filename=file.filename,
        save_debug=False
    )

    return {
        "ok": True,
        "filename": file.filename,
        "result": result,
    }