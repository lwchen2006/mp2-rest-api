# src/data_validator.py
import logging
import pandas as pd


logger = logging.getLogger(__name__)


def validate_dataframe(df, required_columns, numeric_columns):
    """Validate the DataFrame and return valid data.

    required_columns: a list of column names that must exist.
    numeric_columns: a list of column names whose values should be numeric.
    """
    rows_before = len(df)
    df = df.copy()

    # 1. Every required column must exist
    for col in required_columns:
        if col not in df.columns:
            logger.error("Missing required column: %s", col)
            raise ValueError(f"Missing required column: {col}")

    # 2. Numeric columns: drop rows whose non-missing values are not numbers
    for col in numeric_columns:
        if col not in df.columns:
            logger.error("Missing numeric column: %s", col)
            raise ValueError(f"Missing numeric column: {col}")

        invalid_rows = []
        for i, value in df[col].items():
            if pd.notna(value):
                try:
                    float(value)
                except (ValueError, TypeError):
                    invalid_rows.append(i)

        if invalid_rows:
            logger.warning(
                "Removed %d rows with invalid numeric values in %s",
                len(invalid_rows),
                col,
            )
            df = df.drop(index=invalid_rows)

        # convert to a numeric data type
        df[col] = pd.to_numeric(df[col])

    logger.debug(
        "Validation: %d → %d rows (%d removed)",
        rows_before,
        len(df),
        rows_before - len(df),
    )
    return df