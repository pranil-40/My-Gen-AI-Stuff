from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = ("credits_attempted", "credits_earned", "grade_points")


def _empty_result() -> dict[str, float | str]:
    return {
        "gpa": 0.0,
        "pace": 0.0,
        "calculated_status": "VIOLATION",
    }


def calculate_sap_metrics(course_data: list[dict[str, Any]] | str | Path) -> dict[str, float | str]:
    try:
        if isinstance(course_data, (str, Path)):
            df = pd.read_csv(course_data)
        else:
            df = pd.DataFrame(course_data)

        if df.empty or any(column not in df.columns for column in REQUIRED_COLUMNS):
            return _empty_result()

        df = df.loc[:, REQUIRED_COLUMNS].apply(pd.to_numeric, errors="coerce").fillna(0)

        total_credits_attempted = float(df["credits_attempted"].sum())
        total_credits_earned = float(df["credits_earned"].sum())
        total_grade_points = float(df["grade_points"].sum())

        if total_credits_attempted <= 0:
            return _empty_result()

        gpa = total_grade_points / total_credits_attempted
        pace = (total_credits_earned / total_credits_attempted) * 100

        return {
            "gpa": float(gpa),
            "pace": float(pace),
            "calculated_status": "PASS" if gpa >= 2.0 and pace >= 67 else "VIOLATION",
        }
    except (OSError, ValueError, TypeError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return _empty_result()
