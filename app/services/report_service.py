from datetime import datetime
import json
from markupsafe import escape


def _result_html(result):
    if isinstance(result, dict) and isinstance(result.get("columns"), list) and isinstance(result.get("records"), list):
        columns = result["columns"]
        records = result["records"][:30]
        head = "".join(f"<th>{escape(col)}</th>" for col in columns)
        rows = []
        for row in records:
            cells = "".join(f"<td>{escape(row.get(col, ''))}</td>" for col in columns)
            rows.append(f"<tr>{cells}</tr>")
        note = "<p class='small'>仅展示前 30 条结果。</p>" if len(result["records"]) > 30 else ""
        return f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>{note}"
    return f"<pre>{escape(json.dumps(result, ensure_ascii=False, indent=2, default=str)[:8000])}</pre>"


def build_report_html(dataset, analyses, ai_messages):
    analysis_sections = []
    for task in analyses:
        params = escape(json.dumps(task.params, ensure_ascii=False, default=str))
        analysis_sections.append(
            f"""
            <section>
              <h2>{escape(task.name)}</h2>
              <p><strong>分析类型：</strong>{escape(task.analysis_type)}</p>
              <p><strong>分析参数：</strong><code>{params}</code></p>
              {_result_html(task.result)}
            </section>
            """
        )

    cleaning_rows = ""
    for record in sorted(dataset.cleaning_records, key=lambda item: item.created_at):
        cleaning_rows += (
            "<tr>"
            f"<td>{escape(record.operation)}</td>"
            f"<td>{record.before_rows}</td>"
            f"<td>{record.after_rows}</td>"
            f"<td>{escape(record.created_at.strftime('%Y-%m-%d %H:%M'))}</td>"
            "</tr>"
        )
    cleaning_section = ""
    if cleaning_rows:
        cleaning_section = f"""
        <section>
          <h2>数据清洗记录</h2>
          <table><thead><tr><th>操作</th><th>处理前行数</th><th>处理后行数</th><th>时间</th></tr></thead>
          <tbody>{cleaning_rows}</tbody></table>
        </section>
        """

    ai_section = ""
    if ai_messages:
        rows = "".join(
            f"<li><strong>{'用户' if m.role == 'user' else '助手'}：</strong>{escape(m.content)}</li>"
            for m in ai_messages[-10:]
        )
        ai_section = f"<section><h2>AI 分析记录</h2><ul>{rows}</ul></section>"

    quality = dataset.quality
    field_rows = "".join(
        "<tr>"
        f"<td>{escape(item.get('name', ''))}</td>"
        f"<td>{escape(item.get('dtype', ''))}</td>"
        f"<td>{item.get('missing_count', 0)}</td>"
        f"<td>{item.get('missing_rate', 0)}%</td>"
        f"<td>{item.get('unique_count', 0)}</td>"
        f"<td>{item.get('outlier_count', 0)}</td>"
        "</tr>"
        for item in quality.get("columns", [])
    )

    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{escape(dataset.name)} 数据分析报告</title>
<style>
body{{font-family:Arial,'Microsoft YaHei',sans-serif;line-height:1.7;max-width:980px;margin:40px auto;color:#253044}}
h1,h2{{color:#173a6b}} section{{margin:28px 0;padding:20px;border:1px solid #d9e2ef;border-radius:10px}}
table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #d9e2ef;padding:8px;text-align:left}}
th{{background:#eef3fb}} pre{{white-space:pre-wrap;word-break:break-word;background:#f6f8fb;padding:12px}}
code{{background:#f3f5f8;padding:2px 5px;border-radius:4px;word-break:break-all}}
.small{{color:#667085;font-size:14px}} .table-wrap{{overflow-x:auto}}
</style>
</head>
<body>
<h1>{escape(dataset.name)} 数据分析报告</h1>
<p class="small">生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<section>
<h2>数据集概况</h2>
<table>
<tr><th>原始文件</th><td>{escape(dataset.original_name)}</td></tr>
<tr><th>数据规模</th><td>{dataset.row_count} 行 × {dataset.col_count} 列</td></tr>
<tr><th>数据健康度</th><td>{quality.get('health_score', '-')} 分</td></tr>
<tr><th>缺失单元格</th><td>{quality.get('missing_cells', '-')}</td></tr>
<tr><th>重复行</th><td>{quality.get('duplicate_rows', '-')}</td></tr>
<tr><th>异常值数量</th><td>{quality.get('outlier_count', '-')}</td></tr>
</table>
</section>
<section>
<h2>字段质量</h2>
<table><thead><tr><th>字段</th><th>类型</th><th>缺失</th><th>缺失率</th><th>唯一值</th><th>异常值</th></tr></thead>
<tbody>{field_rows}</tbody></table>
</section>
{cleaning_section}
{''.join(analysis_sections) if analysis_sections else '<section><h2>分析结果</h2><p>尚未保存分析任务。</p></section>'}
{ai_section}
<section>
<h2>结论</h2>
<p>本报告由 InsightPilot 根据真实数据处理和统计计算结果自动生成。分析结论应结合数据来源、采样范围和业务背景进行解释。</p>
</section>
</body>
</html>
"""
