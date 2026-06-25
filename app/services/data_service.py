from pathlib import Path
import math
import numpy as np
import pandas as pd


def read_dataframe(path, nrows=None):
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        last_error = None
        for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
            try:
                return pd.read_csv(path, encoding=encoding, nrows=nrows)
            except UnicodeDecodeError as exc:
                last_error = exc
        raise ValueError(f"CSV 编码无法识别：{last_error}")
    if suffix in {".xls", ".xlsx"}:
        return pd.read_excel(path, nrows=nrows)
    raise ValueError("仅支持 CSV、XLS、XLSX 文件。")


def dataframe_to_records(df, limit=30):
    safe = df.head(limit).replace({np.nan: None})
    return safe.astype(object).where(pd.notnull(safe), None).to_dict(orient="records")


def normalize_scalar(value):
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def infer_columns(df):
    result = []
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            kind = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(s):
            kind = "datetime"
        else:
            kind = "text"
        result.append({
            "name": str(col),
            "dtype": str(s.dtype),
            "kind": kind,
            "missing": int(s.isna().sum()),
            "unique": int(s.nunique(dropna=True)),
        })
    return result


def outlier_summary(df):
    summary = {}
    numeric = df.select_dtypes(include=np.number)
    for col in numeric.columns:
        s = numeric[col].dropna()
        if s.empty:
            summary[str(col)] = 0
            continue
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            count = 0
        else:
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            count = int(((s < lower) | (s > upper)).sum())
        summary[str(col)] = count
    return summary


def quality_report(df):
    rows, cols = df.shape
    total_cells = max(rows * cols, 1)
    missing_cells = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())
    missing_rate = round(missing_cells / total_cells * 100, 2)
    duplicate_rate = round(duplicate_rows / max(rows, 1) * 100, 2)
    outliers = outlier_summary(df)
    outlier_count = int(sum(outliers.values()))

    health_score = 100
    health_score -= min(45, missing_rate * 0.8)
    health_score -= min(25, duplicate_rate * 0.8)
    health_score -= min(20, outlier_count / max(rows, 1) * 100 * 0.2)
    health_score = max(0, round(health_score, 1))

    columns = []
    for col in df.columns:
        s = df[col]
        item = {
            "name": str(col),
            "dtype": str(s.dtype),
            "missing_count": int(s.isna().sum()),
            "missing_rate": round(float(s.isna().mean() * 100), 2),
            "unique_count": int(s.nunique(dropna=True)),
            "outlier_count": int(outliers.get(str(col), 0)),
        }
        if pd.api.types.is_numeric_dtype(s):
            desc = s.describe()
            for key in ("mean", "std", "min", "25%", "50%", "75%", "max"):
                item[key] = normalize_scalar(desc.get(key))
        columns.append(item)

    return {
        "rows": int(rows),
        "cols": int(cols),
        "missing_cells": missing_cells,
        "missing_rate": missing_rate,
        "duplicate_rows": duplicate_rows,
        "duplicate_rate": duplicate_rate,
        "outlier_count": outlier_count,
        "health_score": health_score,
        "columns": columns,
    }


def save_dataframe(df, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def clean_dataframe(df, operation, params):
    result = df.copy()

    if operation == "drop_duplicates":
        result = result.drop_duplicates()

    elif operation == "drop_missing":
        columns = params.get("columns") or list(result.columns)
        result = result.dropna(subset=columns)

    elif operation == "fill_missing":
        columns = params.get("columns") or list(result.columns)
        strategy = params.get("strategy", "mean")
        constant = params.get("constant", "")
        for col in columns:
            if col not in result.columns:
                continue
            if strategy == "mean" and pd.api.types.is_numeric_dtype(result[col]):
                value = result[col].mean()
            elif strategy == "median" and pd.api.types.is_numeric_dtype(result[col]):
                value = result[col].median()
            elif strategy == "mode":
                modes = result[col].mode(dropna=True)
                value = modes.iloc[0] if not modes.empty else constant
            elif strategy == "constant":
                value = constant
            else:
                continue
            result[col] = result[col].fillna(value)

    elif operation == "strip_strings":
        columns = params.get("columns") or list(result.select_dtypes(include="object").columns)
        for col in columns:
            if col in result.columns:
                result[col] = result[col].map(lambda x: x.strip() if isinstance(x, str) else x)

    elif operation == "remove_outliers":
        columns = params.get("columns") or list(result.select_dtypes(include=np.number).columns)
        mask = pd.Series(True, index=result.index)
        for col in columns:
            if col not in result.columns or not pd.api.types.is_numeric_dtype(result[col]):
                continue
            s = result[col]
            q1, q3 = s.quantile([0.25, 0.75])
            iqr = q3 - q1
            if iqr == 0:
                continue
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            mask &= s.isna() | s.between(lower, upper)
        result = result[mask]

    elif operation in {"zscore", "minmax"}:
        columns = params.get("columns") or list(result.select_dtypes(include=np.number).columns)
        for col in columns:
            if col not in result.columns or not pd.api.types.is_numeric_dtype(result[col]):
                continue
            s = result[col]
            if operation == "zscore":
                std = s.std()
                if std and not pd.isna(std):
                    result[col] = (s - s.mean()) / std
            else:
                min_v, max_v = s.min(), s.max()
                if max_v != min_v:
                    result[col] = (s - min_v) / (max_v - min_v)

    else:
        raise ValueError("不支持的数据清洗操作。")

    return result.reset_index(drop=True)
