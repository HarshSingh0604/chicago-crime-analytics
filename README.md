# Chicago Crime Analytics

An end-to-end data project on Chicago crime records: a Python pipeline cleans the raw data, loads it into a SQLite database, runs exploratory and statistical analysis, builds SQL summary tables and views, and saves charts. A Flask web app sits on top for managing records and browsing the results.

## What it does

| Step | Script | What happens |
|---|---|---|
| Use Case 1 | `1.py` | Loads the raw crime CSV, cleans it (types, missing values, derived Month / DayOfWeek / Hour columns) and writes it to the `crimes` table in SQLite |
| Use Case 2 | `2.py` | Exploratory analysis: crime trend over the years, top 10 crime categories, arrest rate by year, a month x day-of-week heatmap and the top 10 community areas |
| Use Case 3 | `3.py` | Statistical insights: crimes by hour of day, crime distribution across community areas and a correlation matrix |
| Use Case 4 | `4.py` | SQL reporting: summary tables, SQL queries and database views (`vw_crime_yearly`, `vw_crime_by_category`) read back into Pandas and charted |

`pipeline.py` runs all four steps in order. Charts are saved to `output/charts/`.

## Web app

The Flask app in `web_app/` has five tabs:

1. **Crime database management**: browse, filter, add, edit and delete records, upload a CSV to replace the data, and rerun the full pipeline
2. **Use Case 1**: loading and cleaning results
3. **Use Case 2**: exploratory charts
4. **Use Case 3**: statistical insights
5. **Use Case 4**: SQL summary tables and views

## Tech stack

Python, Pandas, NumPy, SQLAlchemy, SQLite, Matplotlib, Seaborn, Flask, HTML/CSS (Jinja templates)

## Project structure

```
.
├── 1.py ... 4.py        # the four use cases
├── pipeline.py          # runs 1.py -> 4.py
├── data/                # raw Chicago crime data and lookup tables
└── web_app/
    ├── app.py           # Flask routes
    ├── db.py            # database connection and column definitions
    ├── data_cleaning.py # cleaning used for CSV uploads
    ├── templates/
    └── static/
```

## Running it

```bash
pip install -r requirements.txt

# 1. Build the database and charts
python pipeline.py

# 2. Start the web app
cd web_app
python app.py
```

Then open http://127.0.0.1:5000.

Optionally set `FLASK_SECRET_KEY` in your environment; otherwise a random key is generated each time the app starts.

## Data

The `data/` folder holds a sample of the City of Chicago crime dataset plus lookup tables for IUCR codes, community areas, police districts, beats and ward offices.
