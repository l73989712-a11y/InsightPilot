from flask import render_template, request, jsonify, flash
from flask_login import login_required, current_user
from . import bp
from ...extensions import db
from ...models import Dataset, AnalysisTask
from ...services.data_service import read_dataframe
from ...services.analysis_service import execute_analysis


def get_owned_dataset(dataset_id):
    return Dataset.query.filter_by(id=dataset_id, user_id=current_user.id).first_or_404()


@bp.route("/<int:dataset_id>")
@login_required
def workbench(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    tasks = AnalysisTask.query.filter_by(dataset_id=dataset.id).order_by(AnalysisTask.created_at.desc()).limit(20).all()
    numeric_columns = [c["name"] for c in dataset.columns if c.get("kind") == "numeric"]
    other_columns = [c["name"] for c in dataset.columns if c.get("kind") != "numeric"]
    return render_template(
        "analysis/workbench.html",
        dataset=dataset,
        tasks=tasks,
        numeric_columns=numeric_columns,
        other_columns=other_columns,
    )


@bp.route("/<int:dataset_id>/run", methods=["POST"])
@login_required
def run(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    payload = request.get_json(silent=True) or request.form.to_dict(flat=True)
    action = payload.get("action")
    params = payload.get("params", {})
    if isinstance(params, str):
        import json
        params = json.loads(params or "{}")

    try:
        df = read_dataframe(dataset.active_path)
        output = execute_analysis(df, action, params)
        task = AnalysisTask(
            dataset_id=dataset.id,
            user_id=current_user.id,
            name=payload.get("name") or action,
            analysis_type=action,
            status="success",
        )
        task.params = params
        task.result = output["result"]
        task.chart = output["chart"]
        db.session.add(task)
        db.session.commit()
        return jsonify({"ok": True, "task_id": task.id, **output})
    except Exception as exc:
        db.session.rollback()
        return jsonify({"ok": False, "message": str(exc)}), 400


@bp.route("/task/<int:task_id>")
@login_required
def task_detail(task_id):
    task = AnalysisTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    return jsonify({
        "id": task.id,
        "name": task.name,
        "analysis_type": task.analysis_type,
        "result": task.result,
        "chart": task.chart,
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M"),
    })
