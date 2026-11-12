import os
from datetime import datetime
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename


def allowed_extension(filename: str, allowed: set[str]) -> bool:
    ext = os.path.splitext(filename or "")[1].lower()
    return ext in allowed


def save_upload(file_storage, subfolder: str, prefix: str, allowed: set[str]) -> str:
    if not file_storage or not file_storage.filename:
        raise ValueError("Please choose a file to upload.")
    if not allowed_extension(file_storage.filename, allowed):
        raise ValueError("Unsupported file type.")
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    max_size = current_app.config.get("MAX_UPLOAD_SIZE", 5 * 1024 * 1024)
    if size > max_size:
        raise ValueError("File is too large. Maximum size is 5 MB.")
    name = secure_filename(file_storage.filename)
    if not name:
        raise ValueError("Invalid file name.")
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    stored = f"{prefix}_{stamp}_{uuid4().hex[:10]}_{name}"
    path = os.path.join(folder, stored)
    file_storage.save(path)
    return os.path.join(subfolder, stored).replace("\\", "/")


def absolute_upload_path(relative_path: str) -> str:
    if not relative_path:
        return ""
    upload_root = os.path.realpath(current_app.config["UPLOAD_FOLDER"])
    full_path = os.path.realpath(os.path.join(upload_root, relative_path))
    try:
        within_upload_root = os.path.commonpath((upload_root, full_path)) == upload_root
    except ValueError:
        within_upload_root = False
    if not within_upload_root:
        return ""
    return full_path


def delete_upload(relative_path: str) -> None:
    if not relative_path:
        return
    full = absolute_upload_path(relative_path)
    if os.path.isfile(full):
        os.remove(full)
