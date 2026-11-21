# use_case4.py
# Use Case 4 - MySQL Reporting & Integration (implemented in SQLite)

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, text
import os


# ---------------------------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------------------------

DATABASE_URL = "sqlite:///chicago_crime.db"
engine = create_engine(DATABASE_URL)

output_dir = "output/charts"
os.makedirs(output_dir, exist_ok=True)


try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1 FROM crimes LIMIT 1"))

    print("Connected to database. 'crimes' table found.")

except Exception as e:
    print(f"ERROR: Could not access 'crimes' table - {e}")
    print("Make sure '1.py' has been run first to create the database.")
    raise


# ---------------------------------------------------------------------------
# TASK 1: DESIGN & POPULATE SUMMARY TABLES
# ---------------------------------------------------------------------------

with engine.begin() as conn:

    # Yearly summary table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS crime_summary_yearly (
            year INTEGER PRIMARY KEY,
            total_crimes INTEGER,
            total_arrests INTEGER
        );
    """))

    # Crime-category summary table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS crime_summary_by_category (
            primary_type TEXT PRIMARY KEY,
            crime_count INTEGER,
            percentage REAL
        );
    """))

    # Refresh derived summary tables from the current crimes table
    conn.execute(
        text("DELETE FROM crime_summary_yearly;")
    )

    conn.execute(
        text("DELETE FROM crime_summary_by_category;")
    )

    # Populate yearly summary
    conn.execute(text("""
        INSERT INTO crime_summary_yearly
            (year, total_crimes, total_arrests)
        SELECT
            year,
            COUNT(*),
            SUM(
                CASE
                    WHEN arrest = 1 THEN 1
                    ELSE 0
                END
            )
        FROM crimes
        GROUP BY year
        ORDER BY year;
    """))

    # Populate crime-category summary
    conn.execute(text("""
        INSERT INTO crime_summary_by_category
            (primary_type, crime_count, percentage)
        SELECT
            primary_type,
            COUNT(*),
            ROUND(
                COUNT(*) * 100.0 /
                (SELECT COUNT(*) FROM crimes),
                2
            )
        FROM crimes
        GROUP BY primary_type;
    """))


print("\nSummary tables refreshed from current 'crimes' data.")


print("\nContents of crime_summary_yearly:")

print(
    pd.read_sql(
        "SELECT * FROM crime_summary_yearly ORDER BY year",
        con=engine
    )
)


print("\nContents of crime_summary_by_category (top 10 shown):")

print(
    pd.read_sql(
        """
        SELECT *
        FROM crime_summary_by_category
        ORDER BY crime_count DESC
        LIMIT 10
        """,
        con=engine
    )
)


# ---------------------------------------------------------------------------
# TASK 2: SQL QUERIES
# ---------------------------------------------------------------------------

with engine.connect() as conn:

    # Crime count per year
    crime_count_per_year = pd.read_sql(
        text("""
            SELECT
                year,
                COUNT(*) AS crime_count
            FROM crimes
            GROUP BY year
            ORDER BY year
        """),
        conn
    )

    print("\nCrime count per year:")
    print(crime_count_per_year)

    # Top 5 crime types and percentages
    top5_crime_types = pd.read_sql(
        text("""
            SELECT
                primary_type,
                COUNT(*) AS crime_count,
                ROUND(
                    COUNT(*) * 100.0 /
                    (SELECT COUNT(*) FROM crimes),
                    2
                ) AS percentage
            FROM crimes
            GROUP BY primary_type
            ORDER BY crime_count DESC
            LIMIT 5
        """),
        conn
    )

    print("\nTop 5 crime types and their percentages:")
    print(top5_crime_types)

    # Arrest count per year
    arrest_count_per_year = pd.read_sql(
        text("""
            SELECT
                year,
                SUM(
                    CASE
                        WHEN arrest = 1 THEN 1
                        ELSE 0
                    END
                ) AS arrest_count
            FROM crimes
            GROUP BY year
            ORDER BY year
        """),
        conn
    )

    print("\nArrest count per year:")
    print(arrest_count_per_year)


# ---------------------------------------------------------------------------
# TASK 3: CREATE DATABASE VIEWS
# ---------------------------------------------------------------------------

with engine.begin() as conn:

    conn.execute(text("""
        CREATE VIEW IF NOT EXISTS vw_crime_yearly AS
        SELECT
            year,
            COUNT(*) AS total_crimes,
            SUM(
                CASE
                    WHEN arrest = 1 THEN 1
                    ELSE 0
                END
            ) AS total_arrests
        FROM crimes
        GROUP BY year;
    """))

    conn.execute(text("""
        CREATE VIEW IF NOT EXISTS vw_crime_by_category AS
        SELECT
            primary_type,
            COUNT(*) AS crime_count,
            ROUND(
                COUNT(*) * 100.0 /
                (SELECT COUNT(*) FROM crimes),
                2
            ) AS percentage
        FROM crimes
        GROUP BY primary_type;
    """))


print("\nViews 'vw_crime_yearly' and 'vw_crime_by_category' are ready.")


# ---------------------------------------------------------------------------
# TASK 4: READ VIEWS INTO PANDAS
# ---------------------------------------------------------------------------

vw_yearly_df = pd.read_sql(
    """
    SELECT *
    FROM vw_crime_yearly
    ORDER BY year
    """,
    con=engine
)

vw_category_df = pd.read_sql(
    """
    SELECT *
    FROM vw_crime_by_category
    ORDER BY crime_count DESC
    """,
    con=engine
)


print("\nvw_crime_yearly (from view):")
print(vw_yearly_df)


print("\nvw_crime_by_category (from view, top 10 shown):")
print(vw_category_df.head(10))


# ---------------------------------------------------------------------------
# TASK 5: VISUALIZE DATA READ FROM THE VIEWS
# ---------------------------------------------------------------------------

# Yearly crimes vs arrests
plt.figure(figsize=(10, 5))

plt.plot(
    vw_yearly_df["year"],
    vw_yearly_df["total_crimes"],
    marker="o",
    label="Total Crimes"
)

plt.plot(
    vw_yearly_df["year"],
    vw_yearly_df["total_arrests"],
    marker="o",
    label="Total Arrests"
)

plt.title("Yearly Crimes vs Arrests (from vw_crime_yearly)")
plt.xlabel("Year")
plt.ylabel("Count")
plt.legend()
plt.grid(True)
plt.tight_layout()

plt.savefig(
    f"{output_dir}/vw_crime_yearly.png"
)

plt.show()


# Top 10 crime categories
top10_view = vw_category_df.head(10)

plt.figure(figsize=(10, 6))

sns.barplot(
    x="percentage",
    y="primary_type",
    data=top10_view
)

plt.title(
    "Top 10 Crime Categories by % "
    "(from vw_crime_by_category)"
)

plt.xlabel("Percentage of Total Crimes")
plt.ylabel("Primary Type")
plt.tight_layout()

plt.savefig(
    f"{output_dir}/vw_crime_by_category.png"
)

plt.show()


# ---------------------------------------------------------------------------
# EXPORT REPORTS
# ---------------------------------------------------------------------------

reports_dir = "output/reports"
os.makedirs(reports_dir, exist_ok=True)

vw_yearly_df.to_csv(
    f"{reports_dir}/crime_yearly_report.csv",
    index=False
)

vw_category_df.to_csv(
    f"{reports_dir}/crime_by_category_report.csv",
    index=False
)

print(
    f"\nReports exported to '{reports_dir}/'."
)

print("\nUse Case 4 completed successfully.")