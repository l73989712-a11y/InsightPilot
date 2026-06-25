import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from .data_service import normalize_scalar


ALLOWED_ACTIONS = {
    "describe",
    "value_counts",
    "group_aggregate",
    "correlation",
    "time_trend",
    "pivot_table",
    "linear_regression",
    "kmeans",
}


def validate_columns(df, columns):
    for col in columns:
        if col and col not in df.columns:
            raise ValueError(f"字段不存在：{col}")


def _records(df, limit=200):
    safe = df.head(limit).replace({np.nan: None})
    return safe.astype(object).where(pd.notnull(safe), None).to_dict(orient="records")


def execute_analysis(df, action, params):
    if action not in ALLOWED_ACTIONS:
        raise ValueError("分析操作不在安全白名单中。")

    if action == "describe":
        result_df = df.describe(include="all").transpose().reset_index().rename(columns={"index": "字段"})
        result = {"columns": list(result_df.columns), "records": _records(result_df)}
        chart = {}

    elif action == "value_counts":
        column = params.get("column")
        validate_columns(df, [column])
        top_n = min(int(params.get("top_n", 20)), 100)
        counts = df[column].fillna("缺失值").astype(str).value_counts().head(top_n)
        result_df = counts.rename_axis(column).reset_index(name="数量")
        result = {"columns": list(result_df.columns), "records": _records(result_df)}
        chart = {
            "title": {"text": f"{column} 频数分布", "left": "center"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": result_df[column].tolist(), "axisLabel": {"rotate": 25}},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "data": result_df["数量"].tolist()}],
        }

    elif action == "group_aggregate":
        group_by = params.get("group_by") or []
        metrics = params.get("metrics") or []
        if isinstance(group_by, str):
            group_by = [group_by]
        validate_columns(df, group_by + [m.get("column") for m in metrics])
        agg_map = {}
        for metric in metrics:
            method = metric.get("method", "mean")
            if method not in {"mean", "sum", "count", "max", "min", "median"}:
                raise ValueError(f"不支持的聚合方法：{method}")
            agg_map[metric["column"]] = method
        if not group_by or not agg_map:
            raise ValueError("分组字段和聚合字段不能为空。")
        result_df = df.groupby(group_by, dropna=False).agg(agg_map).reset_index()
        result_df.columns = [
            "_".join([str(x) for x in col if x]) if isinstance(col, tuple) else str(col)
            for col in result_df.columns
        ]
        result = {"columns": list(result_df.columns), "records": _records(result_df)}
        x_col = result_df.columns[0]
        y_cols = list(result_df.columns[1:])
        chart = {
            "title": {"text": params.get("title", "分组聚合结果"), "left": "center"},
            "tooltip": {"trigger": "axis"},
            "legend": {"top": 30},
            "xAxis": {"type": "category", "data": result_df[x_col].astype(str).tolist(), "axisLabel": {"rotate": 25}},
            "yAxis": {"type": "value"},
            "series": [
                {"name": col, "type": params.get("chart_type", "bar"), "data": [normalize_scalar(v) for v in result_df[col].tolist()]}
                for col in y_cols
            ],
        }

    elif action == "correlation":
        columns = params.get("columns") or list(df.select_dtypes(include=np.number).columns)
        validate_columns(df, columns)
        columns = list(dict.fromkeys(columns))
        numeric = df[columns].select_dtypes(include=np.number)
        if numeric.shape[1] < 2:
            raise ValueError("相关分析至少需要两个数值字段。")
        corr = numeric.corr().round(4)
        result_df = corr.reset_index().rename(columns={"index": "字段"})
        result = {"columns": list(result_df.columns), "records": _records(result_df)}
        data = []
        for i, row_name in enumerate(corr.index):
            for j, col_name in enumerate(corr.columns):
                data.append([j, i, normalize_scalar(corr.loc[row_name, col_name])])
        chart = {
            "title": {"text": "相关系数热力图", "left": "center"},
            "tooltip": {"position": "top"},
            "xAxis": {"type": "category", "data": corr.columns.tolist(), "splitArea": {"show": True}},
            "yAxis": {"type": "category", "data": corr.index.tolist(), "splitArea": {"show": True}},
            "visualMap": {"min": -1, "max": 1, "calculable": True, "orient": "horizontal", "left": "center", "bottom": 0},
            "series": [{"type": "heatmap", "data": data, "label": {"show": True}}],
        }

    elif action == "time_trend":
        time_col = params.get("time_column")
        value_col = params.get("value_column")
        method = params.get("method", "mean")
        freq = params.get("freq", "M")
        validate_columns(df, [time_col, value_col])
        if method not in {"mean", "sum", "count", "max", "min"}:
            raise ValueError("时间趋势聚合方法不合法。")
        temp = df[[time_col, value_col]].copy()
        temp[time_col] = pd.to_datetime(temp[time_col], errors="coerce")
        temp = temp.dropna(subset=[time_col])
        if temp.empty:
            raise ValueError("时间字段无法转换为有效日期。")
        temp = temp.set_index(time_col)
        grouped = getattr(temp[value_col].resample(freq), method)().reset_index()
        grouped[time_col] = grouped[time_col].astype(str)
        result = {"columns": list(grouped.columns), "records": _records(grouped)}
        chart = {
            "title": {"text": f"{value_col} 时间趋势", "left": "center"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": grouped[time_col].tolist()},
            "yAxis": {"type": "value"},
            "series": [{"type": "line", "smooth": True, "data": [normalize_scalar(v) for v in grouped[value_col].tolist()]}],
        }

    elif action == "pivot_table":
        index = params.get("index")
        columns = params.get("columns")
        values = params.get("values")
        aggfunc = params.get("aggfunc", "mean")
        validate_columns(df, [index, columns, values])
        if aggfunc not in {"mean", "sum", "count", "max", "min", "median"}:
            raise ValueError("透视表聚合方法不合法。")
        pivot = pd.pivot_table(df, index=index, columns=columns, values=values, aggfunc=aggfunc, fill_value=0)
        result_df = pivot.reset_index()
        result_df.columns = [str(c) for c in result_df.columns]
        result = {"columns": list(result_df.columns), "records": _records(result_df)}
        chart = {}

    elif action == "linear_regression":
        x_col = params.get("x")
        y_col = params.get("y")
        validate_columns(df, [x_col, y_col])
        if x_col == y_col:
            raise ValueError("自变量和因变量不能是同一字段。")
        temp = df[[x_col, y_col]].dropna()
        if len(temp) < 3:
            raise ValueError("线性回归至少需要3条有效数据。")
        X = temp[[x_col]].astype(float).values
        y = temp[y_col].astype(float).values
        model = LinearRegression().fit(X, y)
        pred = model.predict(X)
        result = {
            "coefficient": normalize_scalar(model.coef_[0]),
            "intercept": normalize_scalar(model.intercept_),
            "r2": normalize_scalar(model.score(X, y)),
            "sample_size": int(len(temp)),
        }
        points = [[normalize_scalar(a), normalize_scalar(b)] for a, b in zip(temp[x_col], temp[y_col])]
        line_points = sorted([[normalize_scalar(a), normalize_scalar(b)] for a, b in zip(temp[x_col], pred)], key=lambda x: x[0])
        chart = {
            "title": {"text": f"{x_col} 与 {y_col} 线性回归", "left": "center"},
            "tooltip": {"trigger": "item"},
            "xAxis": {"type": "value", "name": x_col},
            "yAxis": {"type": "value", "name": y_col},
            "series": [
                {"name": "原始数据", "type": "scatter", "data": points},
                {"name": "回归线", "type": "line", "showSymbol": False, "data": line_points},
            ],
        }

    elif action == "kmeans":
        columns = params.get("columns") or []
        n_clusters = max(2, min(int(params.get("n_clusters", 3)), 8))
        validate_columns(df, columns)
        columns = list(dict.fromkeys(columns))
        temp = df[columns].dropna()
        if len(columns) < 2:
            raise ValueError("K-Means 至少选择两个数值字段。")
        if len(temp) < n_clusters:
            raise ValueError("有效样本数量少于聚类数量。")
        X = temp.astype(float)
        model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = model.fit_predict(X)
        result_df = temp.copy()
        result_df["cluster"] = labels
        result = {
            "columns": list(result_df.columns),
            "records": _records(result_df),
            "centers": [[normalize_scalar(v) for v in row] for row in model.cluster_centers_],
            "inertia": normalize_scalar(model.inertia_),
        }
        chart = {
            "title": {"text": "K-Means 聚类结果", "left": "center"},
            "tooltip": {},
            "xAxis": {"type": "value", "name": columns[0]},
            "yAxis": {"type": "value", "name": columns[1]},
            "series": [
                {
                    "name": f"簇 {cluster}",
                    "type": "scatter",
                    "data": [
                        [normalize_scalar(row[columns[0]]), normalize_scalar(row[columns[1]])]
                        for _, row in result_df[result_df["cluster"] == cluster].iterrows()
                    ],
                }
                for cluster in range(n_clusters)
            ],
        }

    return {"result": result, "chart": chart}
