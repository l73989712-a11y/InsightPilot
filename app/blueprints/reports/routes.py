from flask import render_template, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from . import bp
from ...extensions import db
from ...models import Dataset, Report, AnalysisTask, AIConversation, AIMessage
from ...services.report_service import build_report_html


def get_owned_dataset(dataset_id):
    return Dataset.query.filter_by(id=dataset_id, user_id=current_user.id).first_or_404()


@bp.route("/")
@login_required
def list_reports():
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template("reports/list.html", reports=reports)


@bp.route("/generate/<int:dataset_id>", methods=["POST"])
@login_required
def generate(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    analyses = AnalysisTask.query.filter_by(
        dataset_id=dataset.id, user_id=current_user.id
    ).order_by(AnalysisTask.created_at.asc()).all()

    conversation_ids = [
        c.id for c in AIConversation.query.filter_by(
            dataset_id=dataset.id, user_id=current_user.id
        ).all()
    ]
    ai_messages = AIMessage.query.filter(AIMessage.conversation_id.in_(conversation_ids)).all() if conversation_ids else []

    html = build_report_html(dataset, analyses, ai_messages)
    report = Report(
        user_id=current_user.id,
        dataset_id=dataset.id,
        title=f"{dataset.name} 数据分析报告",
        summary="系统根据数据质量、统计分析和 AI 分析记录自动生成。",
        content_html=html,
    )
    db.session.add(report)
    db.session.commit()
    flash("报告生成完成。", "success")
    return redirect(url_for("reports.detail", report_id=report.id))


@bp.route("/<int:report_id>")
@login_required
def detail(report_id):
    report = Report.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()
    return render_template("reports/detail.html", report=report)


@bp.route("/<int:report_id>/export")
@login_required
def export(report_id):
    report = Report.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()
    return Response(
        report.content_html,
        mimetype="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="report_{report.id}.html"'},
    )
