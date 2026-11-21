from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_SOURCE_COLUMNS = [
    "id",
    "case_number",
    "date",
    "block",
    "iucr_code",
    "primary_type",
    "description",
    "location_desc",
    "arrest",
    "domestic",
    "beat_num",
    "district_code",
    "ward_no",
    "community_code",
    "fbi_code",
    "x_coordinate",
    "y_coordinate",
    "year",
    "date_of_update",
    "latitude",
    "longitude",
    "location",
]



def clean_crime_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the same core cleaning/feature-engineering logic used in UC1.

    This helper is intentionally scoped to cleaning. Database creation and
    database replacement are handled by Flask, not by this function.
    """
    missing_columns = [
        col for col in REQUIRED_SOURCE_COLUMNS if col not in df.columns
    ]
    if missing_columns:
        raise ValueError(
            "Uploaded CSV is missing required columns: "
            + ", ".join(missing_columns)
        )

    df = df.copy()

    # Date conversion.
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Remove exact duplicate rows.
    df.drop_duplicates(inplace=True)

    # Handle selected key/important missing fields exactly as UC1.
    df["location_desc"] = df["location_desc"].fillna("UNKNOWN")

    df["ward_no"] = df["ward_no"].astype("Int64")
    df["community_code"] = df["community_code"].astype("Int64")

    ward_mode = df["ward_no"].mode()
    community_mode = df["community_code"].mode()

    if not ward_mode.empty:
        df["ward_no"] = df["ward_no"].fillna(ward_mode.iloc[0])
    if not community_mode.empty:
        df["community_code"] = df["community_code"].fillna(
            community_mode.iloc[0]
        )

    # Standardize all string/categorical columns.
    categorical_cols = df.select_dtypes(
        include=["object", "string"]
    ).columns
    for col in categorical_cols:
        df[col] = df[col].str.strip().str.upper()

    # Feature engineering.
    df["Year"] = df["date"].dt.year
    df["Month"] = df["date"].dt.month
    df["DayOfWeek"] = df["date"].dt.day_name()
    df["Hour"] = df["date"].dt.hour

    # Keep the original source `year`; drop redundant generated `Year`.
    if "Year" in df.columns:
        if "year" in df.columns:
            if not (df["year"] == df["Year"]).all():
                raise ValueError(
                    "Uploaded data contains different values in 'year' and generated 'Year'."
                )
        df.drop(columns=["Year"], inplace=True)

    # Safety validation for the primary key used by the existing schema.
    if df["id"].isna().any():
        raise ValueError("The uploaded data contains missing values in 'id'.")
    if df["id"].duplicated().any():
        raise ValueError("The uploaded data contains duplicate 'id' values.")

    # Preserve only the existing 25-column database schema.
    db_columns = [
        "id",
        "case_number",
        "date",
        "block",
        "iucr_code",
        "primary_type",
        "description",
        "location_desc",
        "arrest",
        "domestic",
        "beat_num",
        "district_code",
        "ward_no",
        "community_code",
        "fbi_code",
        "x_coordinate",
        "y_coordinate",
        "year",
        "date_of_update",
        "latitude",
        "longitude",
        "location",
        "Month",
        "DayOfWeek",
        "Hour",
    ]

    return df[db_columns]
