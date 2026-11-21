#use_case1.py
#Use Case 1 - Load and Clean Chicago Crime Data

import pandas as pd
import numpy as np
from sqlalchemy import (
    create_engine,MetaData, Table, Column,
    Integer, Float, String, DateTime, Boolean, text
)

DATABASE_URL = "sqlite:///chicago_crime.db"

#load and read the csv file
try:
    df = pd.read_csv("data/chicago_crime_dataset.csv")
except FileNotFoundError:
    print("ERROR: 'data/chicago_crime_dataset.csv' not found. "
          "Make sure the CSV is in the 'data' folder relative to this script.")
    raise

print("\nFirst 10 Rows:")
print(df.head(10))
print("\nDataset Shape:")
print(df.shape)
print(f"\nNo. of rows:{df.shape[0]}")
print(f"No. of columns:{df.shape[1]}")
print("\nColumn names and data types:")
print(df.dtypes)
print("\nMissing values in each column:")
print(df.isnull().sum())

#convert date column to datetime
df['date'] = pd.to_datetime(df['date'], errors='coerce')
print("\nData type of date column after conversion:")
print(df['date'].dtype)

print("\nNumber of duplicate rows:")
print(df.duplicated().sum())
df.drop_duplicates(inplace=True)

df['location_desc'] = df['location_desc'].fillna('UNKNOWN')

print("\nSample rows with missing values:")
print(df[df.isnull().any(axis=1)].head(10))

df['ward_no'] = df['ward_no'].astype('Int64')
df['community_code'] = df['community_code'].astype('Int64')
df['ward_no'] = df['ward_no'].fillna(df['ward_no'].mode()[0])
df['community_code'] = df['community_code'].fillna(df['community_code'].mode()[0])

print("\nMissing values in key fields after handling:")
print(df[['ward_no', 'community_code']].isnull().sum())

categorical_cols = df.select_dtypes(include=['object', 'string']).columns
print(categorical_cols)
for col in categorical_cols:
    df[col] = df[col].str.strip().str.upper()

print("\nCategorical columns after standardization:")
print(df[categorical_cols].head(10))

print("\nDate column:")
print(df['date'].head())

df['Year'] = df['date'].dt.year
df['Month'] = df['date'].dt.month
df['DayOfWeek'] = df['date'].dt.day_name()
df['Hour'] = df['date'].dt.hour

print("\nNew features generated:")
print(df[['date', 'Year', 'Month', 'DayOfWeek', 'Hour']].head(10))
print("\nFinal number of columns:")
print(df.shape[1])

missing_percentage = np.round((df.isnull().sum().values / len(df)) * 100, 2)
missing_percentage = pd.Series(missing_percentage, index=df.columns)

high_missing_cols = missing_percentage[missing_percentage > 50]

print("\nColumns with more than 50% missing values:")
print(high_missing_cols)

if len(high_missing_cols) > 0:
    df.drop(columns=high_missing_cols.index, inplace=True)
    print("\nColumns with more than 50% missing values were dropped:")
    print(high_missing_cols.index)
else:
    print("\nNo columns have more than 50% missing values. No columns were dropped.")

print("\nFinal DataFrame data types:")
print(df.dtypes)

print(df.describe())
print(df.isnull().sum())

# Compare original year with generated Year
print("\nyear == Year:", (df['year'] == df['Year']).all())

# Keep original lowercase 'year' because it already contains
# the same information as the generated 'Year' column
df.drop('Year', axis=1, inplace=True)

#--- DATABASE ---
try:
    engine = create_engine(DATABASE_URL)

    with engine.connect():
        print("SQLite database connected successfully.")
    print("Database location:", engine.url.database)

    metadata = MetaData()
    crimes_table = Table(
        "crimes", metadata,
        Column("id", Integer, primary_key=True),
        Column("case_number", String(20)),
        Column("date", DateTime),
        Column("block", String(255)),
        Column("iucr_code", Integer),
        Column("primary_type", String(150)),
        Column("description", String(500)),
        Column("location_desc", String(150)),
        Column("arrest", Boolean),
        Column("domestic", Boolean),
        Column("beat_num", Integer),
        Column("district_code", Integer),
        Column("ward_no", Integer),
        Column("community_code", Integer),
        Column("fbi_code", String(10)),
        Column("x_coordinate", Float),
        Column("y_coordinate", Float),
        Column("year", Integer),
        Column("date_of_update", String(50)),
        Column("latitude", Float),
        Column("longitude", Float),
        Column("location", String(100)),
        Column("Month", Integer),
        Column("DayOfWeek", String(20)),
        Column("Hour", Integer)
    )
    metadata.create_all(engine)
    print("\n'crimes' table is ready.")

    with engine.connect() as connection:
        record_count = connection.execute(text("SELECT COUNT(*) FROM crimes")).scalar()

    if record_count == 0:
        df.to_sql(name="crimes", con=engine, if_exists="append", index=False)
        print("\nInitial crime data loaded successfully.")
    else:
        print(f"\n'crimes' table already contains {record_count} records. Existing data was preserved.")

    check_df = pd.read_sql("SELECT * FROM crimes", con=engine)
    print("\nDatabase verification:")
    print("Rows:", len(check_df))
    print("Columns:", len(check_df.columns))
    print("\nFirst 5 rows from the database:")
    print(check_df.head())

    record_count_df = pd.read_sql("SELECT COUNT(*) AS Total_Records FROM crimes", engine)
    print("\nRecord count in crimes table:")
    print(record_count_df)

except Exception as e:
    print(f"\nDatabase operation failed: {e}")
    raise

print(f"There are {df['primary_type'].nunique()} unique crime types in the dataset.")
print("Date Data Type :", df["date"].dtype)
print("\nMissing Dates :", df["date"].isnull().sum())
print("\nEarliest Date :", df["date"].min())
print("Latest Date   :", df["date"].max())