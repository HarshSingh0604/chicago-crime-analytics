from __future__ import annotations

from datetime import datetime
from math import ceil
from pathlib import Path
import os
import secrets
import subprocess
import sys


import pandas as pd
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from sqlalchemy import create_engine , text, inspect

from db import BASE_DIR, DB_COLUMNS, EDITABLE_FORM_FIELDS, engine
from data_cleaning import clean_crime_data


app = Flask(__name__)
# Set FLASK_SECRET_KEY in your environment; a random key is used otherwise.
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

PER_PAGE = 20


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def parse_datetime(value: str) -> datetime:
    """Parse HTML datetime-local values into Python datetime objects."""
    if not value:
        raise ValueError("Date is required.")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Invalid date format.") from exc



def parse_optional_int(value: str):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"'{value}' must be an integer.") from exc



def parse_bool(value: str) -> int:
    return 1 if value in {"1", "true", "True", "on", "yes"} else 0



def normalize_form_text(value: str, unknown_if_blank: bool = False) -> str | None:
    value = (value or "").strip().upper()
    if not value:
        return "UNKNOWN" if unknown_if_blank else None
    return value



def form_data_from_request(form) -> dict:
    date_value = parse_datetime(form.get("date", ""))

    return {
        "case_number": normalize_form_text(form.get("case_number")),
        "date": date_value,
        "block": normalize_form_text(form.get("block")),
        "primary_type": normalize_form_text(form.get("primary_type")),
        "description": normalize_form_text(form.get("description")),
        "location_desc": normalize_form_text(
            form.get("location_desc"), unknown_if_blank=True
        ),
        "arrest": parse_bool(form.get("arrest", "0")),
        "domestic": parse_bool(form.get("domestic", "0")),
        "beat_num": parse_optional_int(form.get("beat_num")),
        "district_code": parse_optional_int(form.get("district_code")),
        "ward_no": parse_optional_int(form.get("ward_no")),
        "community_code": parse_optional_int(form.get("community_code")),
        "year": date_value.year,
        "Month": date_value.month,
        "DayOfWeek": date_value.strftime("%A"),
        "Hour": date_value.hour,
        "date_of_update": datetime.now(),
    }



def get_record(record_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM crimes WHERE id = :id"),
            {"id": record_id},
        ).mappings().first()
    return dict(row) if row else None



def record_for_form(record: dict | None) -> dict:
    if not record:
        return {}
    result = record.copy()
    date_value = result.get("date")
    if date_value is not None:
        if hasattr(date_value, "strftime"):
            result["date_form"] = date_value.strftime("%Y-%m-%dT%H:%M")
        else:
            parsed = pd.to_datetime(date_value, errors="coerce")
            result["date_form"] = (
                parsed.strftime("%Y-%m-%dT%H:%M") if not pd.isna(parsed) else ""
            )
    else:
        result["date_form"] = ""
    return result


# ---------------------------------------------------------------------------
# Static chart/report serving
# ---------------------------------------------------------------------------

@app.route("/charts/<path:filename>")
def chart_file(filename: str):
    return send_from_directory(BASE_DIR / "output" / "charts", filename)


@app.route("/reports/<path:filename>")
def report_file(filename: str):
    return send_from_directory(
        BASE_DIR / "output" / "reports",
        filename,
        as_attachment=True,
    )


# ---------------------------------------------------------------------------
# Main navigation
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return redirect(url_for("tab1"))


@app.route("/tab1")
def tab1():
    page = max(request.args.get("page", 1, type=int), 1)
    query = request.args.get("q", "").strip()

    # ---------------------------------------------------------
    # Columns displayed even before the database is initialized
    # ---------------------------------------------------------

    default_columns = [
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

    # ---------------------------------------------------------
    # Check whether the crimes table exists
    # ---------------------------------------------------------

    database_ready = inspect(engine).has_table("crimes")

    # ---------------------------------------------------------
    # Fresh-project state:
    # Database exists/opens, but crimes table has not been created
    # ---------------------------------------------------------

    if not database_ready:

        return render_template(
            "tab1.html",
            records=[],
            columns=default_columns,
            stats={
                "total_records": 0,
                "total_columns": len(default_columns),
                "database": Path(engine.url.database).name,
                "primary_key": "id",
            },
            page=1,
            total_pages=1,
            query=query,
            database_ready=False,
        )

    # ---------------------------------------------------------
    # Normal state — crimes table exists
    # ---------------------------------------------------------

    offset = (page - 1) * PER_PAGE

    where_clause = ""
    params = {
        "limit": PER_PAGE,
        "offset": offset,
    }

    if query:
        where_clause = """
            WHERE CAST(id AS TEXT) LIKE :q
               OR case_number LIKE :q
               OR primary_type LIKE :q
               OR block LIKE :q
               OR description LIKE :q
        """

        params["q"] = f"%{query.upper()}%"

    with engine.connect() as conn:

        total_records = conn.execute(
            text(f"SELECT COUNT(*) FROM crimes {where_clause}"),
            params if query else {},
        ).scalar_one()

        rows = conn.execute(
            text(f"""
                SELECT *
                FROM crimes
                {where_clause}
                ORDER BY id DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        ).mappings().all()

    total_pages = max(ceil(total_records / PER_PAGE), 1)

    if page > total_pages:
        return redirect(
            url_for(
                "tab1",
                page=total_pages,
                q=query
            )
        )

    stats = {
        "total_records": total_records
        if not query
        else get_total_records_without_filter(),
        "total_columns": 25,
        "database": Path(engine.url.database).name,
        "table": "crimes",
        "primary_key": "id",
    }

    return render_template(
        "tab1.html",
        records=[dict(row) for row in rows],
        columns=list(rows[0].keys()) if rows else default_columns,
        stats=stats,
        page=page,
        total_pages=total_pages,
        query=query,
        database_ready=True,
    )



def get_total_records_without_filter() -> int:
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM crimes")).scalar_one()


@app.route("/tab1/refresh")
def refresh_records():
    return redirect(url_for("tab1", q=request.args.get("q", "")))


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

@app.route("/tab1/add", methods=["GET", "POST"])
def add_record():
    if request.method == "GET":

        with engine.connect() as conn:
            next_id = conn.execute(
                text("""
                    SELECT COALESCE(MAX(id), 0) + 1
                    FROM crimes
                """)
            ).scalar_one()

        return render_template(
            "add_edit_crime.html",
            mode="add",
            record={},
            fields=EDITABLE_FORM_FIELDS,
            display_id=next_id,
        )

    try:
        data = form_data_from_request(request.form)
        if not data["case_number"] or not data["date"] or not data["primary_type"]:
            raise ValueError("Case number, date and primary type are required.")

        insert_sql = text("""
            INSERT INTO crimes (
                case_number, date, block, primary_type, description,
                location_desc, arrest, domestic, beat_num, district_code,
                ward_no, community_code, year, date_of_update,
                Month, DayOfWeek, Hour
            ) VALUES (
                :case_number, :date, :block, :primary_type, :description,
                :location_desc, :arrest, :domestic, :beat_num, :district_code,
                :ward_no, :community_code, :year, :date_of_update,
                :Month, :DayOfWeek, :Hour
            )
        """)

        with engine.begin() as conn:
            conn.execute(insert_sql, data)

        flash("Crime record created successfully.", "success")
        return redirect(url_for("tab1"))

    except Exception as exc:
        flash(f"Could not create record: {exc}", "error")
        return render_template(
            "add_edit_crime.html",
            mode="add",
            record=request.form,
            fields=EDITABLE_FORM_FIELDS,
        ), 400


# ---------------------------------------------------------------------------
# READ / DETAIL
# ---------------------------------------------------------------------------

@app.route("/tab1/view/<int:record_id>")
def view_record(record_id: int):
    record = get_record(record_id)
    if not record:
        flash("Record not found.", "error")
        return redirect(url_for("tab1"))
    return render_template("record_detail.html", record=record)


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

@app.route("/tab1/edit/<int:record_id>", methods=["GET", "POST"])
def edit_record(record_id: int):
    existing = get_record(record_id)
    if not existing:
        flash("Record not found.", "error")
        return redirect(url_for("tab1"))

    if request.method == "GET":
        return render_template(
            "add_edit_crime.html",
            mode="edit",
            record=record_for_form(existing),
            fields=EDITABLE_FORM_FIELDS,
        )

    try:
        data = form_data_from_request(request.form)
        if not data["case_number"] or not data["date"] or not data["primary_type"]:
            raise ValueError("Case number, date and primary type are required.")

        update_sql = text("""
            UPDATE crimes
            SET case_number = :case_number,
                date = :date,
                block = :block,
                primary_type = :primary_type,
                description = :description,
                location_desc = :location_desc,
                arrest = :arrest,
                domestic = :domestic,
                beat_num = :beat_num,
                district_code = :district_code,
                ward_no = :ward_no,
                community_code = :community_code,
                year = :year,
                date_of_update = :date_of_update,
                Month = :Month,
                DayOfWeek = :DayOfWeek,
                Hour = :Hour
            WHERE id = :id
        """)

        data["id"] = record_id

        with engine.begin() as conn:
            conn.execute(update_sql, data)

        flash("Crime record updated successfully.", "success")
        return redirect(url_for("view_record", record_id=record_id))

    except Exception as exc:
        flash(f"Could not update record: {exc}", "error")
        form_record = request.form.to_dict()
        form_record["date_form"] = request.form.get("date", "")
        return render_template(
            "add_edit_crime.html",
            mode="edit",
            record=form_record,
            fields=EDITABLE_FORM_FIELDS,
            record_id=record_id,
        ), 400


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

@app.post("/tab1/delete/<int:record_id>")
def delete_record(record_id: int):
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM crimes WHERE id = :id"),
                {"id": record_id},
            )

        if result.rowcount == 0:
            flash("Record not found.", "error")
        else:
            flash("Crime record deleted successfully.", "success")

    except Exception as exc:
        flash(f"Could not delete record: {exc}", "error")

    return redirect(url_for("tab1"))


# ---------------------------------------------------------------------------
# CSV Upload - replace current contents after confirmation
# ---------------------------------------------------------------------------

@app.post("/tab1/upload")
def upload_csv():
    uploaded_file = request.files.get("file")
    upload_mode = request.form.get("upload_mode")

    # ---------------------------------------------------------------
    # Basic file validation
    # ---------------------------------------------------------------

    if not uploaded_file or not uploaded_file.filename:
        flash("Please select a CSV file.", "error")
        return redirect(url_for("tab1"))

    if not uploaded_file.filename.lower().endswith(".csv"):
        flash("Only CSV files are allowed.", "error")
        return redirect(url_for("tab1"))

    # ---------------------------------------------------------------
    # Validate selected upload mode
    # ---------------------------------------------------------------

    if upload_mode not in {"replace", "append"}:
        flash("Please select a valid upload operation.", "error")
        return redirect(url_for("tab1"))

    # ---------------------------------------------------------------
    # Validate confirmation checkbox
    # ---------------------------------------------------------------

    if request.form.get("confirm_upload") != "yes":
        flash(
            "Please confirm that you understand the selected "
            "upload operation.",
            "error"
        )
        return redirect(url_for("tab1"))

    try:
        # -----------------------------------------------------------
        # Read uploaded CSV
        # -----------------------------------------------------------

        raw_df = pd.read_csv(uploaded_file.stream)

        # Use the same cleaning logic as Use Case 1
        cleaned_df = clean_crime_data(raw_df)

        # -----------------------------------------------------------
        # MODE 1: REPLACE ALL CURRENT RECORDS
        # -----------------------------------------------------------

        if upload_mode == "replace":

            with engine.begin() as conn:

                # Remove current rows but keep the existing table/schema
                conn.execute(text("DELETE FROM crimes"))

                # Insert cleaned uploaded records
                cleaned_df.to_sql(
                    name="crimes",
                    con=conn,
                    if_exists="append",
                    index=False,
                )

            flash(
                f"{len(cleaned_df)} records uploaded and replaced "
                "successfully.",
                "success"
            )

        # -----------------------------------------------------------
        # MODE 2: ADD ONLY NEW RECORDS
        # -----------------------------------------------------------

        else:

            with engine.begin() as conn:

                # ---------------------------------------------------
                # 1. Check duplicate IDs inside uploaded CSV
                # ---------------------------------------------------

                duplicate_ids = (
                    cleaned_df[
                        cleaned_df["id"].duplicated(keep=False)
                    ]["id"]
                    .dropna()
                    .unique()
                )

                if len(duplicate_ids) > 0:
                    raise ValueError(
                        "The uploaded CSV contains duplicate IDs. "
                        f"Duplicate IDs found: "
                        f"{duplicate_ids[:10].tolist()}"
                    )

                # ---------------------------------------------------
                # 2. Get existing IDs from database
                # ---------------------------------------------------

                existing_ids = set(
                    conn.execute(
                        text("SELECT id FROM crimes")
                    ).scalars().all()
                )

                # ---------------------------------------------------
                # 3. Check uploaded IDs against existing IDs
                # ---------------------------------------------------

                id_conflicts = cleaned_df[
                    cleaned_df["id"].isin(existing_ids)
                ]

                if not id_conflicts.empty:
                    raise ValueError(
                        f"{len(id_conflicts)} uploaded records contain "
                        "IDs that already exist in the database."
                    )

                # ---------------------------------------------------
                # 4. Remove duplicate/same records inside upload
                #
                # A record is considered the same when these fields
                # match:
                #   case_number
                #   date
                #   primary_type
                #   block
                # ---------------------------------------------------

                before_dedup = len(cleaned_df)

                cleaned_df = cleaned_df.drop_duplicates(
                    subset=[
                        "case_number",
                        "date",
                        "primary_type",
                        "block",
                    ]
                )

                duplicates_inside_upload = (
                    before_dedup - len(cleaned_df)
                )

                # ---------------------------------------------------
                # 5. Read identifying fields from existing DB records
                # ---------------------------------------------------

                existing_records = conn.execute(
                    text("""
                        SELECT
                            case_number,
                            date,
                            primary_type,
                            block
                        FROM crimes
                    """)
                ).fetchall()

                existing_keys = {
                    (
                        row.case_number,
                        row.date,
                        row.primary_type,
                        row.block,
                    )
                    for row in existing_records
                }

                # ---------------------------------------------------
                # 6. Create identifying keys for uploaded records
                # ---------------------------------------------------

                upload_keys = cleaned_df.apply(
                    lambda row: (
                        row["case_number"],
                        row["date"],
                        row["primary_type"],
                        row["block"],
                    ),
                    axis=1,
                )

                # ---------------------------------------------------
                # 7. Find records already present in database
                # ---------------------------------------------------

                already_exists = upload_keys.isin(existing_keys)

                existing_record_count = int(
                    already_exists.sum()
                )

                # Keep only genuinely new records
                cleaned_df = cleaned_df.loc[
                    ~already_exists
                ].copy()

                # ---------------------------------------------------
                # 8. Insert only new records
                # ---------------------------------------------------

                if cleaned_df.empty:

                    flash(
                        "No new records were added. All uploaded "
                        "records already exist in the database or "
                        "were duplicates within the uploaded file.",
                        "info"
                    )

                else:

                    cleaned_df.to_sql(
                        name="crimes",
                        con=conn,
                        if_exists="append",
                        index=False,
                    )

                    flash(
                        f"{len(cleaned_df)} new records added "
                        f"successfully. "
                        f"{duplicates_inside_upload} duplicate rows "
                        f"inside the upload were removed, and "
                        f"{existing_record_count} records already "
                        "present in the database were skipped.",
                        "success"
                    )

    except Exception as e:

        flash(
            f"Upload failed: {e}",
            "error"
        )

    return redirect(url_for("tab1"))


# ---------------------------------------------------------------------------
# Static showcase with required dynamic changes to tabs 2-5
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Static showcase with required dynamic changes to tabs 2-5
# ---------------------------------------------------------------------------

@app.route("/tab2")
def tab2():
    try:
        with engine.connect() as conn:

            # ---------------------------------------------------------
            # Basic dataset information
            # ---------------------------------------------------------

            total_records = conn.execute(
                text("SELECT COUNT(*) FROM crimes")
            ).scalar_one()

            unique_crime_types = conn.execute(
                text("SELECT COUNT(DISTINCT primary_type) FROM crimes")
            ).scalar_one()

            missing_dates = conn.execute(
                text("SELECT COUNT(*) FROM crimes WHERE date IS NULL")
            ).scalar_one()

            date_range = conn.execute(
                text("""
                    SELECT MIN(date), MAX(date)
                    FROM crimes
                """)
            ).one()

            earliest_date = date_range[0]
            latest_date = date_range[1]

            # ---------------------------------------------------------
            # Task 2 - Missing-value handling
            # ---------------------------------------------------------

            all_data = pd.read_sql(
                "SELECT * FROM crimes",
                con=conn
            )

            missing_summary = (
                all_data.isnull()
                .sum()
                .reset_index()
            )

            missing_summary.columns = [
                "column",
                "missing_count"
            ]

            # Show only columns that currently contain missing values.
            missing_summary = missing_summary[
                missing_summary["missing_count"] > 0
            ].copy()

            # Describe how the missing values were handled.
            missing_summary["handling"] = missing_summary["column"].map({
                "location_desc": "Filled with UNKNOWN",
                "ward_no": "Filled with mode (0 missing after handling)",
                "community_code": "Filled with mode (0 missing after handling)",
                "x_coordinate": (
                    "Not filled because it was not considered a key field "
                    "for the current analysis."
                ),
                "y_coordinate": (
                    "Not filled because it was not considered a key field "
                    "for the current analysis."
                ),
                "latitude": (
                    "Not filled because it was not considered a key field "
                    "for the current analysis."
                ),
                "longitude": (
                    "Not filled because it was not considered a key field "
                    "for the current analysis."
                ),
            })

            missing_summary["handling"] = missing_summary["handling"].fillna(
                "Handled during cleaning"
            )

            # ward_no and community_code had missing values before cleaning,
            # but now contain no missing values because they were filled
            # using their respective modes.
            existing_columns = set(missing_summary["column"])

            if "location_desc" not in existing_columns:
                missing_summary.loc[len(missing_summary)] = [
                    "location_desc",
                    "0 (Handled before database insertion)",
                    "Filled with UNKNOWN"
                ]


            if "ward_no" not in existing_columns:
                missing_summary.loc[len(missing_summary)] = [
                    "ward_no",
                    "0 (Handled before database insertion)",
                    "Filled with mode"
                ]

            if "community_code" not in existing_columns:
                missing_summary.loc[len(missing_summary)] = [
                    "community_code",
                    "0 (Handled before database insertion)",
                    "Filled with mode"
                ]

            missing_summary = missing_summary.to_dict("records")

            # ---------------------------------------------------------
            # Task 1 - First 10 rows from the current crimes table
            # ---------------------------------------------------------

            first_rows = conn.execute(
                text("""
                    SELECT *
                    FROM crimes
                    ORDER BY id ASC
                    LIMIT 10
                """)
            ).mappings().all()

            # ---------------------------------------------------------
            # Task 1 - Schema and data types
            # ---------------------------------------------------------

            schema_rows = conn.execute(
                text("PRAGMA table_info(crimes)")
            ).mappings().all()

        total_columns = len(DB_COLUMNS)

        return render_template(
            "tab2.html",
            total_records=total_records,
            total_columns=total_columns,
            unique_crime_types=unique_crime_types,
            missing_dates=missing_dates,
            earliest_date=earliest_date,
            latest_date=latest_date,
            first_rows=first_rows,
            schema_rows=schema_rows,
            missing_summary=missing_summary,
        )

    except Exception as e:
        flash(f"Could not load Use Case 1 results: {e}", "error")
        return render_template("tab2.html")


@app.route("/tab3")
def tab3():
    try:
        with engine.connect() as conn:

            # ---------------------------------------------------------
            # Q1 - Most frequent crime category
            # ---------------------------------------------------------

            most_frequent_row = conn.execute(
                text("""
                    SELECT primary_type, COUNT(*) AS crime_count
                    FROM crimes
                    GROUP BY primary_type
                    ORDER BY crime_count DESC
                    LIMIT 1
                """)
            ).mappings().first()

            most_frequent_crime = (
                most_frequent_row["primary_type"]
                if most_frequent_row
                else "N/A"
            )

            most_frequent_crime_count = (
                most_frequent_row["crime_count"]
                if most_frequent_row
                else 0
            )

            # ---------------------------------------------------------
            # Q2 - Arrest-rate consistency across years
            # ---------------------------------------------------------

            arrest_by_year = pd.read_sql(
                text("""
                    SELECT
                        year,
                        AVG(arrest) * 100 AS arrest_rate
                    FROM crimes
                    GROUP BY year
                    ORDER BY year
                """),
                con=conn
            )

            if not arrest_by_year.empty:
                min_arrest_rate = arrest_by_year["arrest_rate"].min()
                max_arrest_rate = arrest_by_year["arrest_rate"].max()

                arrest_rate_range = (
                    max_arrest_rate - min_arrest_rate
                )

                arrest_rate_std = (
                    arrest_by_year["arrest_rate"].std()
                )

                arrest_rate_consistent = (
                    arrest_rate_range < 5
                )
            else:
                min_arrest_rate = 0
                max_arrest_rate = 0
                arrest_rate_range = 0
                arrest_rate_std = 0
                arrest_rate_consistent = False

            # ---------------------------------------------------------
            # Q3 - Month with highest crime frequency
            # ---------------------------------------------------------

            highest_month_row = conn.execute(
                text("""
                    SELECT Month, COUNT(*) AS crime_count
                    FROM crimes
                    GROUP BY Month
                    ORDER BY crime_count DESC
                    LIMIT 1
                """)
            ).mappings().first()

            month_names = {
                1: "January",
                2: "February",
                3: "March",
                4: "April",
                5: "May",
                6: "June",
                7: "July",
                8: "August",
                9: "September",
                10: "October",
                11: "November",
                12: "December",
            }

            if highest_month_row:
                highest_crime_month = month_names.get(
                    int(highest_month_row["Month"]),
                    str(highest_month_row["Month"])
                )

                highest_crime_month_count = (
                    highest_month_row["crime_count"]
                )
            else:
                highest_crime_month = "N/A"
                highest_crime_month_count = 0

        return render_template(
            "tab3.html",
            most_frequent_crime=most_frequent_crime,
            most_frequent_crime_count=most_frequent_crime_count,
            min_arrest_rate=min_arrest_rate,
            max_arrest_rate=max_arrest_rate,
            arrest_rate_range=arrest_rate_range,
            arrest_rate_std=arrest_rate_std,
            arrest_rate_consistent=arrest_rate_consistent,
            highest_crime_month=highest_crime_month,
            highest_crime_month_count=highest_crime_month_count,
        )

    except Exception as e:
        flash(f"Could not load Use Case 2 results: {e}", "error")
        return render_template("tab3.html")


@app.route("/tab4")
def tab4():
    return render_template("tab4.html")


@app.route("/tab5")
def tab5():
    return render_template("tab5.html")


@app.route("/run-pipeline", methods=["POST"])
def run_pipeline():
    try:
        project_root = Path(__file__).resolve().parent.parent
        pipeline_file = project_root / "pipeline.py"

        if not pipeline_file.exists():
            flash(
                "pipeline.py was not found in the project root.",
                "error"
            )
            return redirect(url_for("tab1"))

        result = subprocess.run(
            [sys.executable, str(pipeline_file)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            flash(
                "Complete pipeline finished successfully. "
                "Use Cases 1, 2, 3, and 4 have been executed.",
                "success"
            )
        else:
            error_message = (
                result.stderr.strip()
                or result.stdout.strip()
                or "Unknown pipeline error."
            )

            flash(
                f"Pipeline failed: {error_message}",
                "error"
            )

    except Exception as e:
        flash(
            f"Could not run the pipeline: {e}",
            "error"
        )

    return redirect(url_for("tab1"))

if __name__ == "__main__":
    app.run(debug=True)