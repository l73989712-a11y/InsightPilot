"""检查 InsightPilot 的 Python、依赖、目录和数据库配置。"""
from __future__ import annotations
import importlib
from importlib.metadata import PackageNotFoundError, version
import os
import platform
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "flask": "Flask",
    "flask_login": "Flask-Login",
    "flask_sqlalchemy": "Flask-SQLAlchemy",
    "flask_wtf": "Flask-WTF",
    "pymysql": "PyMySQL",
    "pandas": "pandas",
    "numpy": "numpy",
    "sklearn": "scikit-learn",
    "openpyxl": "openpyxl",
    "xlrd": "xlrd",
    "dotenv": "python-dotenv",
    "docx": "python-docx",
    "requests": "requests",
}


def status(ok: bool) -> str:
    return "[OK]" if ok else "[FAIL]"


def main() -> int:
    print("InsightPilot 环境检查")
    print("=" * 48)
    py_ok = (3, 10) <= sys.version_info[:2] <= (3, 12)
    print(status(py_ok), "Python:", platform.python_version(), "（推荐 3.10/3.11）")

    failed = not py_ok
    for module, display in REQUIRED.items():
        try:
            importlib.import_module(module)
            try:
                package_version = version(display)
            except PackageNotFoundError:
                package_version = "已安装"
            print("[OK]", f"{display}: {package_version}")
        except Exception as exc:
            failed = True
            print("[FAIL]", f"{display}: {exc}")

    env_file = ROOT / ".env"
    print(status(env_file.exists()), ".env 配置文件", env_file)
    failed = failed or not env_file.exists()
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
    database_url = os.getenv("DATABASE_URL", "")
    if database_url:
        parsed = urlparse(database_url.replace("mysql+pymysql", "mysql"))
        print("[INFO] 数据库主机:", parsed.hostname or "未识别")
        print("[INFO] 数据库名称:", (parsed.path or "").lstrip("/") or "未识别")
    else:
        print("[WARN] 未设置 DATABASE_URL，请复制 .env.example 为 .env。")

    for rel in ("storage/uploads", "storage/processed", "storage/reports"):
        path = ROOT / rel
        path.mkdir(parents=True, exist_ok=True)
        writable = os.access(path, os.W_OK)
        print(status(writable), "目录可写:", rel)
        failed = failed or not writable

    print("=" * 48)
    print("检查完成。" if not failed else "存在未通过项目，请根据提示处理。")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
