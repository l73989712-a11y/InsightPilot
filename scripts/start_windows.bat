@echo off
chcp 65001 >nul
cd /d %~dp0\..
if not exist .venv (
  echo [1/4] 创建虚拟环境...
  py -3.11 -m venv .venv
)
call .venv\Scripts\activate
if errorlevel 1 exit /b 1
echo [2/4] 安装依赖...
pip install -r requirements.txt
if not exist .env (
  copy .env.example .env >nul
  echo 已生成 .env，请先修改 MySQL 密码后再次运行。
  notepad .env
  exit /b 0
)
echo [3/4] 初始化数据库表...
flask --app run.py init-db
echo [4/4] 启动系统...
python run.py
