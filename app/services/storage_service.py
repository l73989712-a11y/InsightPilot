from pathlib import Path
from uuid import uuid4
from werkzeug.utils import secure_filename


def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def save_upload(file_storage, upload_folder):
    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[1].lower()
    stored_name = f"{uuid4().hex}.{ext}"
    path = Path(upload_folder) / stored_name
    path.parent.mkdir(parents=True, exist_ok=True)
    file_storage.save(path)
    return original, stored_name, str(path), ext


def processed_path(processed_folder, dataset_id, ext="csv"):
    path = Path(processed_folder) / f"dataset_{dataset_id}_processed.{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)
