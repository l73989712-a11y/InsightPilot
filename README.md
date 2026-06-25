# InsightPilot：AI 智能数据分析与可视化平台

这是一个面向 Python Web 应用实训的中小型项目，融合 Flask、MySQL、Pandas、Plotly.js 与大语言模型。

## 一、核心功能

- 用户注册、登录与退出
- CSV / Excel 数据上传和预览
- 数据质量检测：缺失值、重复值、异常值、字段类型
- 数据清洗：去重、删除缺失、缺失值填补、字符串清理、异常值删除、标准化
- 数据分析：描述统计、频数统计、分组聚合、相关分析、时间趋势、数据透视、线性回归、K-Means
- 交互式 Plotly.js 图表
- AI 自然语言数据分析
- 分析历史和 HTML 报告生成
- 规则模式与兼容 OpenAI 接口模式

## 二、运行环境

- Python 3.10 或 3.11
- MySQL 5.7（符合课程数据库版本要求）
- 推荐浏览器：Chrome / Edge

## 三、安装步骤

### 1. 创建虚拟环境

Windows：

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 创建数据库

先在 MySQL 中执行：

```bash
mysql -uroot -p < sql/init.sql
```

或者手动创建：

```sql
CREATE DATABASE insightpilot
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env`，修改数据库账号和密码。

### 5. 初始化数据表

```bash
flask --app run.py init-db
```

### 6. 运行

```bash
python run.py
```

浏览器访问：

```text
http://127.0.0.1:5000
```

## 四、AI 模式

### 规则模式

`.env` 中设置：

```env
LLM_PROVIDER=rule
```

无需网络和密钥，可以识别常见中文分析意图，适合离线答辩。

### 兼容 OpenAI 接口模式

```env
LLM_PROVIDER=openai_compatible
LLM_API_KEY=你的密钥
LLM_BASE_URL=https://你的接口地址/v1
LLM_MODEL=模型名称
```

系统只允许白名单分析动作，不执行模型生成的 Python 代码。

## 五、项目目录

```text
InsightPilot/
├─ app/
│  ├─ blueprints/
│  ├─ services/
│  ├─ static/
│  └─ templates/
├─ docs/
├─ sample_data/
├─ sql/
├─ storage/
├─ tests/
├─ config.py
├─ requirements.txt
└─ run.py
```

## 六、演示建议

1. 注册账号并登录。
2. 上传 `sample_data/student_learning.csv`。
3. 查看数据质量报告。
4. 执行“删除重复数据”或“均值填补缺失值”。
5. 进行“按专业统计平均成绩”的分组聚合。
6. 在 AI 助手输入：`按专业统计平均成绩并绘制柱状图`。
7. 生成综合 HTML 报告。
