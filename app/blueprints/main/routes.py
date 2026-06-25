from flask import render_template
from flask_login import login_required, current_user
from . import bp
from ...models import Dataset, AnalysisTask, Report


@bp.route("/")
@login_required
def dashboard():
    datasets = Dataset.query.filter_by(user_id=current_user.id).order_by(Dataset.created_at.desc()).limit(5).all()
    stats = {
        "datasets": Dataset.query.filter_by(user_id=current_user.id).count(),
        "analyses": AnalysisTask.query.filter_by(user_id=current_user.id).count(),
        "reports": Report.query.filter_by(user_id=current_user.id).count(),
        "rows": sum(d.row_count or 0 for d in Dataset.query.filter_by(user_id=current_user.id).all()),
    }
    return render_template("main/dashboard.html", datasets=datasets, stats=stats)
