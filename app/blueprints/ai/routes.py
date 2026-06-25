from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from . import bp
from ...extensions import db
from ...models import Dataset, AIConversation, AIMessage, AnalysisTask
from ...services.data_service import read_dataframe
from ...services.analysis_service import execute_analysis
from ...services.ai_service import AIService


def get_owned_dataset(dataset_id):
    return Dataset.query.filter_by(id=dataset_id, user_id=current_user.id).first_or_404()


@bp.route("/<int:dataset_id>")
@login_required
def chat(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    conversations = AIConversation.query.filter_by(
        dataset_id=dataset.id, user_id=current_user.id
    ).order_by(AIConversation.created_at.desc()).all()
    messages = conversations[0].messages if conversations else []
    return render_template("ai/chat.html", dataset=dataset, conversations=conversations, messages=messages)


@bp.route("/<int:dataset_id>/ask", methods=["POST"])
@login_required
def ask(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    conversation_id = payload.get("conversation_id")

    if not question:
        return jsonify({"ok": False, "message": "请输入问题。"}), 400

    if conversation_id:
        conversation = AIConversation.query.filter_by(
            id=conversation_id, user_id=current_user.id, dataset_id=dataset.id
        ).first_or_404()
    else:
        conversation = AIConversation(
            user_id=current_user.id,
            dataset_id=dataset.id,
            title=question[:50],
        )
        db.session.add(conversation)
        db.session.flush()

    try:
        user_msg = AIMessage(conversation_id=conversation.id, role="user", content=question)
        db.session.add(user_msg)

        service = AIService(dataset.columns)
        plan = service.plan(question)
        df = read_dataframe(dataset.active_path)
        output = execute_analysis(df, plan["action"], {k: v for k, v in plan.items() if k != "action"})
        summary = service.summarize(question, plan, output["result"])

        assistant_msg = AIMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=summary,
        )
        assistant_msg.plan = plan
        db.session.add(assistant_msg)

        task = AnalysisTask(
            dataset_id=dataset.id,
            user_id=current_user.id,
            name=f"AI：{question[:40]}",
            analysis_type=plan["action"],
            status="success",
        )
        task.params = {k: v for k, v in plan.items() if k != "action"}
        task.result = output["result"]
        task.chart = output["chart"]
        db.session.add(task)
        db.session.commit()

        return jsonify({
            "ok": True,
            "conversation_id": conversation.id,
            "plan": plan,
            "summary": summary,
            "result": output["result"],
            "chart": output["chart"],
        })
    except Exception as exc:
        db.session.rollback()
        return jsonify({"ok": False, "message": str(exc)}), 400
