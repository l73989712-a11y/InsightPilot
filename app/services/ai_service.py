import json
import re
import requests
from flask import current_app
from .analysis_service import ALLOWED_ACTIONS


def _extract_json(text):
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError("模型没有返回可解析的 JSON。")
    return json.loads(match.group(0))


class AIService:
    def __init__(self, columns):
        self.columns = columns
        self.column_names = [c["name"] if isinstance(c, dict) else str(c) for c in columns]
        self.numeric_columns = [
            c["name"] for c in columns if isinstance(c, dict) and c.get("kind") == "numeric"
        ]

    def plan(self, question):
        if current_app.config.get("LLM_PROVIDER") == "openai_compatible":
            try:
                return self._llm_plan(question)
            except Exception:
                return self._rule_plan(question)
        return self._rule_plan(question)

    def summarize(self, question, plan, result):
        if current_app.config.get("LLM_PROVIDER") == "openai_compatible":
            try:
                return self._llm_summary(question, plan, result)
            except Exception:
                pass
        return self._rule_summary(plan, result)

    def _mentioned_columns(self, question):
        return [col for col in self.column_names if col and col in question]

    def _rule_plan(self, question):
        q = question.strip()
        mentioned = self._mentioned_columns(q)

        if "相关" in q or "关系" in q:
            columns = [c for c in mentioned if c in self.numeric_columns]
            if len(columns) < 2:
                columns = self.numeric_columns[: min(6, len(self.numeric_columns))]
            return {"action": "correlation", "columns": columns}

        if "回归" in q or "影响" in q:
            columns = [c for c in mentioned if c in self.numeric_columns]
            if len(columns) < 2:
                columns = self.numeric_columns[:2]
            return {"action": "linear_regression", "x": columns[0], "y": columns[1]}

        if "聚类" in q:
            columns = [c for c in mentioned if c in self.numeric_columns]
            if len(columns) < 2:
                columns = self.numeric_columns[:2]
            return {"action": "kmeans", "columns": columns, "n_clusters": 3}

        if "趋势" in q or "随时间" in q:
            time_col = next((c for c in mentioned if "日期" in c or "时间" in c), None)
            if not time_col:
                time_col = next((c for c in self.column_names if "日期" in c or "时间" in c), None)
            value_col = next((c for c in mentioned if c in self.numeric_columns), None)
            if not value_col and self.numeric_columns:
                value_col = self.numeric_columns[0]
            return {
                "action": "time_trend",
                "time_column": time_col,
                "value_column": value_col,
                "method": "mean",
                "freq": "M",
            }

        if "按" in q and any(word in q for word in ("平均", "总和", "数量", "最大", "最小", "统计")):
            group_candidates = [c for c in mentioned if c not in self.numeric_columns]
            metric_candidates = [c for c in mentioned if c in self.numeric_columns]
            group_col = group_candidates[0] if group_candidates else next(
                (c for c in self.column_names if c not in self.numeric_columns), self.column_names[0]
            )
            metric_col = metric_candidates[0] if metric_candidates else (
                self.numeric_columns[0] if self.numeric_columns else self.column_names[-1]
            )
            method = "mean"
            if "总和" in q or "合计" in q:
                method = "sum"
            elif "数量" in q or "次数" in q:
                method = "count"
            elif "最大" in q:
                method = "max"
            elif "最小" in q:
                method = "min"
            return {
                "action": "group_aggregate",
                "group_by": [group_col],
                "metrics": [{"column": metric_col, "method": method}],
                "chart_type": "bar",
            }

        if "分布" in q or "频数" in q or "占比" in q:
            column = mentioned[0] if mentioned else self.column_names[0]
            return {"action": "value_counts", "column": column, "top_n": 20}

        return {"action": "describe"}

    def _validate_plan(self, plan):
        action = plan.get("action")
        if action not in ALLOWED_ACTIONS:
            raise ValueError("模型返回了不安全的分析动作。")
        return plan

    def _llm_plan(self, question):
        base_url = current_app.config["LLM_BASE_URL"].rstrip("/")
        endpoint = f"{base_url}/chat/completions"
        schema = [{"name": c["name"], "kind": c.get("kind"), "dtype": c.get("dtype")} for c in self.columns]
        prompt = f"""
你是数据分析计划生成器。请将用户问题转换为 JSON，只返回 JSON。
可用动作：describe、value_counts、group_aggregate、correlation、time_trend、
pivot_table、linear_regression、kmeans。
严禁返回 Python 代码、SQL、文件路径或白名单之外的动作。
字段结构：{json.dumps(schema, ensure_ascii=False)}
用户问题：{question}
"""
        payload = {
            "model": current_app.config["LLM_MODEL"],
            "messages": [
                {"role": "system", "content": "你只输出一个合法 JSON 对象。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {current_app.config['LLM_API_KEY']}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=current_app.config["LLM_TIMEOUT"],
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        return self._validate_plan(_extract_json(text))

    def _llm_summary(self, question, plan, result):
        base_url = current_app.config["LLM_BASE_URL"].rstrip("/")
        endpoint = f"{base_url}/chat/completions"
        prompt = f"""
请根据真实计算结果，用中文写一段不超过180字的数据分析结论。
不得编造结果中不存在的数字。
用户问题：{question}
分析计划：{json.dumps(plan, ensure_ascii=False)}
真实结果：{json.dumps(result, ensure_ascii=False, default=str)[:8000]}
"""
        payload = {
            "model": current_app.config["LLM_MODEL"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {current_app.config['LLM_API_KEY']}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=current_app.config["LLM_TIMEOUT"],
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    def _rule_summary(self, plan, result):
        action = plan.get("action")
        if action == "linear_regression":
            r2 = result.get("r2")
            coef = result.get("coefficient")
            return f"线性回归已完成，回归系数为 {coef}，决定系数 R² 为 {r2}。R²越接近1，线性拟合程度越高。"
        if action == "correlation":
            return "相关系数矩阵已生成。系数越接近1或-1，说明两个数值字段的线性关系越强；接近0表示线性关系较弱。"
        if action == "group_aggregate":
            return "系统已按照指定分类字段完成分组聚合，并生成可视化图表。可结合各组数值高低比较不同类别之间的差异。"
        if action == "value_counts":
            return "频数统计已完成，图表展示了该字段中出现次数较多的类别，可用于观察类别分布是否集中或不均衡。"
        if action == "kmeans":
            return "K-Means 聚类已完成。相同簇中的样本在所选数值特征上更加相似，可进一步比较各簇中心解释群体特征。"
        if action == "time_trend":
            return "时间趋势分析已完成。折线图反映指标随时间变化的方向、波动和阶段性特征。"
        return "描述性统计已完成，可重点关注均值、标准差、最小值、最大值以及缺失情况。"
