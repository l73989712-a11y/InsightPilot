"""无需 MySQL 的快速演示模式，仅用于界面预览和功能验证。"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from config import Config
from app.extensions import db


class DemoConfig(Config):
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{ROOT / 'insightpilot_demo.sqlite3'}"
    LLM_PROVIDER = "rule"
    SECRET_KEY = "demo-secret-key-change-before-production"


app = create_app(DemoConfig)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    print("演示模式已启动：http://127.0.0.1:5000")
    print("注意：正式提交和答辩请使用 MySQL 5.7 配置。")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
