Flask web application starter for the Chicago Crime project.

Folder placement:
Move the `web_app` folder into your existing project root, alongside:
- chicago_crime.db
- data/
- output/
- use_case1.py ... use_case4.py

IMPORTANT:
1. The folder should be named `web_app`, not `web app`.
2. The app uses the existing project-level `chicago_crime.db`.
3. Tab 1 is live CRUD + CSV replace-upload.
4. The Add/Edit form intentionally exposes only 12 meaningful fields.
5. The records table/detail view still exposes all 25 database columns.
6. Tabs 2-5 are static showcases using charts already generated in output/charts.

Run from inside web_app:
    python app.py

Then open:
    http://127.0.0.1:5000
