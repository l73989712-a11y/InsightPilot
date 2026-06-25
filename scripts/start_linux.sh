#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  echo "已生成 .env，请修改 MySQL 密码后重新运行。"
  exit 0
fi
flask --app run.py init-db
python run.py
