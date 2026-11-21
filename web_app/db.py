from pathlib import Path

from sqlalchemy import create_engine, inspect, text

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "chicago_crime.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, future=True)

DB_COLUMNS = [
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

EDITABLE_FORM_FIELDS = [
    "case_number",
    "date",
    "block",
    "primary_type",
    "description",
    "location_desc",
    "arrest",
    "domestic",
    "beat_num",
    "district_code",
    "ward_no",
    "community_code",
]


def database_stats() -> dict:
    inspector = inspect(engine)
    columns = inspector.get_columns("crimes")
    pk = inspector.get_pk_constraint("crimes")

    with engine.connect() as conn:
        total_records = conn.execute(
            text("SELECT COUNT(*) FROM crimes")
        ).scalar_one()

    return {
        "total_records": total_records,
        "total_columns": len(columns),
        "table_name": "crimes",
        "database_name": Path(engine.url.database).name,
        "primary_key": (pk.get("constrained_columns") or [None])[0],
    }
