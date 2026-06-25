from pathlib import Path
from flask import render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from . import bp
from ...extensions import db
from ...models import Dataset, CleaningRecord
from ...services.storage_service import allowed_file, save_upload, processed_path
from ...services.data_service import (
    read_dataframe, infer_columns, quality_report, dataframe_to_records,
    save_dataframe, clean_dataframe
)


def get_owned_dataset(dataset_id):
    return Dataset.query.filter_by(id=dataset_id, user_id=current_user.id).first_or_404()


@bp.route("/")
@login_required
def list_datasets():
    datasets = Dataset.query.filter_by(user_id=current_user.id).order_by(Dataset.created_at.desc()).all()
    return render_template("datasets/list.html", datasets=datasets)


@bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        name = request.form.get("name", "").strip()

        if not file or not file.filename:
            flash("请选择文件。", "warning")
            return redirect(request.url)

        if not allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"]):
            flash("仅支持 CSV、XLS、XLSX 文件。", "danger")
            return redirect(request.url)

        try:
            original, stored, path, ext = save_upload(file, current_app.config["UPLOAD_FOLDER"])
            df = read_dataframe(path)
            if len(df) > current_app.config["MAX_ANALYSIS_ROWS"]:
                Path(path).unlink(missing_ok=True)
                flash(f"数据行数超过限制：{current_app.config['MAX_ANALYSIS_ROWS']} 行。", "danger")
                return redirect(request.url)

            dataset = Dataset(
                user_id=current_user.id,
                name=name or Path(original).stem,
                original_name=original,
                stored_name=stored,
                file_type=ext,
                file_path=path,
                size_bytes=Path(path).stat().st_size,
                row_count=len(df),
                col_count=len(df.columns),
            )
            dataset.columns = infer_columns(df)
            dataset.quality = quality_report(df)
            db.session.add(dataset)
            db.session.commit()

            flash("数据集上传并检测完成。", "success")
            return redirect(url_for("datasets.detail", dataset_id=dataset.id))
        except Exception as exc:
            db.session.rollback()
            flash(f"文件处理失败：{exc}", "danger")

    return render_template("datasets/upload.html")


@bp.route("/<int:dataset_id>")
@login_required
def detail(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    df = read_dataframe(dataset.active_path, nrows=current_app.config["DATA_PREVIEW_ROWS"])
    preview = dataframe_to_records(df, current_app.config["DATA_PREVIEW_ROWS"])
    return render_template(
        "datasets/detail.html",
        dataset=dataset,
        preview=preview,
        preview_columns=[str(c) for c in df.columns],
    )


@bp.route("/<int:dataset_id>/clean", methods=["GET", "POST"])
@login_required
def clean(dataset_id):
    dataset = get_owned_dataset(dataset_id)

    if request.method == "POST":
        operation = request.form.get("operation")
        columns = request.form.getlist("columns")
        params = {
            "columns": columns,
            "strategy": request.form.get("strategy", "mean"),
            "constant": request.form.get("constant", ""),
        }
        try:
            df = read_dataframe(dataset.active_path)
            before_rows = len(df)
            cleaned = clean_dataframe(df, operation, params)
            target = processed_path(current_app.config["PROCESSED_FOLDER"], dataset.id)
            save_dataframe(cleaned, target)

            dataset.processed_path = target
            dataset.row_count = len(cleaned)
            dataset.col_count = len(cleaned.columns)
            dataset.columns = infer_columns(cleaned)
            dataset.quality = quality_report(cleaned)

            record = CleaningRecord(
                dataset_id=dataset.id,
                user_id=current_user.id,
                operation=operation,
                before_rows=before_rows,
                after_rows=len(cleaned),
            )
            record.params = params
            db.session.add(record)
            db.session.commit()
            flash("数据清洗完成。", "success")
            return redirect(url_for("datasets.clean", dataset_id=dataset.id))
        except Exception as exc:
            db.session.rollback()
            flash(f"清洗失败：{exc}", "danger")

    records = CleaningRecord.query.filter_by(dataset_id=dataset.id).order_by(CleaningRecord.created_at.desc()).all()
    return render_template("datasets/clean.html", dataset=dataset, records=records)


@bp.route("/<int:dataset_id>/download")
@login_required
def download(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    suffix = Path(dataset.active_path).suffix.lower() or ".csv"
    label = "processed" if dataset.processed_path else "original"
    return send_file(dataset.active_path, as_attachment=True, download_name=f"{dataset.name}_{label}{suffix}")


@bp.route("/<int:dataset_id>/delete", methods=["POST"])
@login_required
def delete(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    for path in {dataset.file_path, dataset.processed_path}:
        if path:
            Path(path).unlink(missing_ok=True)
    db.session.delete(dataset)
    db.session.commit()
    flash("数据集已删除。", "info")
    return redirect(url_for("datasets.list_datasets"))
