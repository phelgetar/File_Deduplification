import mimetypes
import logging

def classify_file(file_info):
    # Basic AI-assisted mock classification based on MIME type
    mime_type, _ = mimetypes.guess_type(str(file_info))
    category = "unknown"

    if mime_type:
        if mime_type.startswith("image"):
            category = "image"
        elif mime_type.startswith("video"):
            category = "video"
        elif mime_type.startswith("audio"):
            category = "audio"
        elif mime_type in ["application/pdf"]:
            category = "document"
        else:
            category = "other"
    else:
        logging.warning(f"Unknown MIME type for {file_info}")

    return {
        "path": str(file_info),
        "category": category,
        "name": file_info.name
    }