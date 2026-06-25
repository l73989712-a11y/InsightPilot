from datetime import datetime, timezone
import json
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db, login_manager


def utcnow_naive():
    """返回不带时区信息的 UTC 时间，兼容 MySQL DATETIME。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JsonMixin:
    @staticmethod
    def _loads(value, default):
        if not value:
            return default
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return default

    @staticmethod
    def _dumps(value):
        return json.dumps(value, ensure_ascii=False, default=str)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)

    datasets = db.relationship("Dataset", backref="owner", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Dataset(JsonMixin, db.Model):
    __tablename__ = "datasets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    processed_path = db.Column(db.String(500))
    size_bytes = db.Column(db.BigInteger, default=0)
    row_count = db.Column(db.Integer, default=0)
    col_count = db.Column(db.Integer, default=0)
    columns_json = db.Column(db.Text)
    quality_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)

    cleaning_records = db.relationship("CleaningRecord", backref="dataset", lazy=True, cascade="all, delete-orphan")
    analysis_tasks = db.relationship("AnalysisTask", backref="dataset", lazy=True, cascade="all, delete-orphan")
    reports = db.relationship("Report", backref="dataset", lazy=True, cascade="all, delete-orphan")

    @property
    def columns(self):
        return self._loads(self.columns_json, [])

    @columns.setter
    def columns(self, value):
        self.columns_json = self._dumps(value)

    @property
    def quality(self):
        return self._loads(self.quality_json, {})

    @quality.setter
    def quality(self, value):
        self.quality_json = self._dumps(value)

    @property
    def active_path(self):
        return self.processed_path or self.file_path


class CleaningRecord(JsonMixin, db.Model):
    __tablename__ = "cleaning_records"

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    operation = db.Column(db.String(50), nullable=False)
    params_json = db.Column(db.Text)
    before_rows = db.Column(db.Integer)
    after_rows = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)

    @property
    def params(self):
        return self._loads(self.params_json, {})

    @params.setter
    def params(self, value):
        self.params_json = self._dumps(value)


class AnalysisTask(JsonMixin, db.Model):
    __tablename__ = "analysis_tasks"

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    analysis_type = db.Column(db.String(50), nullable=False)
    params_json = db.Column(db.Text)
    result_json = db.Column(db.Text)
    chart_json = db.Column(db.Text)
    status = db.Column(db.String(20), default="success", nullable=False)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)

    @property
    def params(self):
        return self._loads(self.params_json, {})

    @params.setter
    def params(self, value):
        self.params_json = self._dumps(value)

    @property
    def result(self):
        return self._loads(self.result_json, {})

    @result.setter
    def result(self, value):
        self.result_json = self._dumps(value)

    @property
    def chart(self):
        return self._loads(self.chart_json, {})

    @chart.setter
    def chart(self, value):
        self.chart_json = self._dumps(value)


class AIConversation(db.Model):
    __tablename__ = "ai_conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)

    messages = db.relationship("AIMessage", backref="conversation", lazy=True, cascade="all, delete-orphan")


class AIMessage(JsonMixin, db.Model):
    __tablename__ = "ai_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("ai_conversations.id"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    plan_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)

    @property
    def plan(self):
        return self._loads(self.plan_json, {})

    @plan.setter
    def plan(self, value):
        self.plan_json = self._dumps(value)


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text)
    content_html = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
