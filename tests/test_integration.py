from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from app import create_app
from app.extensions import db
from config import Config


@pytest.fixture()
def client():
    with TemporaryDirectory() as td:
        class TestConfig(Config):
            TESTING = True
            WTF_CSRF_ENABLED = False
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            UPLOAD_FOLDER = str(Path(td) / "uploads")
            PROCESSED_FOLDER = str(Path(td) / "processed")
            REPORT_FOLDER = str(Path(td) / "reports")
            LLM_PROVIDER = "rule"

        app = create_app(TestConfig)
        with app.app_context():
            db.create_all()
        yield app.test_client()


def login_and_upload(client):
    client.post("/register", data={"username": "tester", "password": "abcdef", "confirm": "abcdef"})
    client.post("/login", data={"username": "tester", "password": "abcdef"})
    path = Path(__file__).parents[1] / "sample_data" / "student_learning.csv"
    with path.open("rb") as file:
        response = client.post(
            "/datasets/upload",
            data={"name": "学生学习数据", "file": (file, path.name)},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    assert response.status_code == 200


def test_full_workflow(client):
    login_and_upload(client)
    analysis = client.post(
        "/analysis/1/run",
        json={
            "action": "group_aggregate",
            "params": {"group_by": ["专业"], "metrics": [{"column": "成绩", "method": "mean"}]},
        },
    )
    assert analysis.status_code == 200
    assert analysis.json["ok"] is True

    ai = client.post("/ai/1/ask", json={"question": "按专业统计平均成绩并绘制柱状图"})
    assert ai.status_code == 200
    assert ai.json["ok"] is True
    assert ai.json["plan"]["action"] == "group_aggregate"

    report = client.post("/reports/generate/1", follow_redirects=True)
    assert report.status_code == 200
    assert "数据分析报告".encode("utf-8") in report.data


def test_invalid_same_regression_column(client):
    login_and_upload(client)
    response = client.post(
        "/analysis/1/run",
        json={"action": "linear_regression", "params": {"x": "成绩", "y": "成绩"}},
    )
    assert response.status_code == 400
    assert response.json["ok"] is False
