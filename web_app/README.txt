Flask web application for the Chicago Crime Analytics project.

It reads the project-level chicago_crime.db and the charts in output/charts,
both created by running the pipeline first (from the project root):

    python pipeline.py

Then start the app from inside web_app:

    python app.py

and open http://127.0.0.1:5000

Tabs:
1. Crime database management: browse, filter, add, edit and delete records,
   replace the data with a CSV upload, and rerun the full pipeline.
   The Add/Edit form exposes the 12 most meaningful fields; the table and
   detail view show all 25 database columns.
2-5. Results of Use Cases 1-4 (cleaning, exploratory analysis, statistical
   insights, SQL reporting).

See ../README.md for the full project overview.
