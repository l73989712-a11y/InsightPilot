import pandas as pd
from app.services.analysis_service import execute_analysis


def sample_df():
    return pd.DataFrame({
        "专业": ["人工智能", "人工智能", "计算机", "计算机"],
        "成绩": [88, 92, 76, 84],
        "学习时长": [5.0, 6.5, 3.5, 4.5],
    })


def test_group_aggregate():
    output = execute_analysis(
        sample_df(),
        "group_aggregate",
        {"group_by": ["专业"], "metrics": [{"column": "成绩", "method": "mean"}]},
    )
    assert output["result"]["records"]
    assert output["chart"]["series"]


def test_correlation():
    output = execute_analysis(sample_df(), "correlation", {"columns": ["成绩", "学习时长"]})
    assert len(output["result"]["records"]) == 2
