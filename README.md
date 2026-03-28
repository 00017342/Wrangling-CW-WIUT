# Data Cleaning & Visualization App
# Developed for the DWV CW by students: 17342 and 18431

This is a simple Streamlit app for uploading, cleaning, and exploring datasets. It helps you quickly understand your data, fix common issues, and create visualizations all in one place.

---

## What it does

**Upload & Overview**

* Supports CSV, Excel, JSON files and Google Sheets
* Shows dataset shape, columns, types, missing values, and duplicates

**Cleaning studio**

* Handle missing values (drop, fill, forward/backward fill)
* Remove duplicates
* Fix data types (numeric, categorical, datetime)
* Clean text (trim, lowercase, mapping)
* Detect and handle outliers
* Scale numeric data
* Rename/drop columns
* Create new columns with formulas
* Group categories or bin numeric data
* Apply validation rules

**Visualization**

* Histogram, box plot, scatter, line, bar, heatmap
* Filter data and choose axes easily
* Safe inputs (no crashes on wrong selections)

**Export**

* See the final metrics of rows, columns, transformations applied, validation violations
* Download cleaned data (CSV/Excel)
* Export a workflow recipe (JSON) that records all steps, changes, affected columns, rows and metadata
* Export a replay pandas script or test it on your dataset
* See the detailed transformations log

---

## Tech Stack

* Python
* Streamlit
* Pandas
* Matplotlib

---

## AI Assistance

AI tools were used during development as support for brainstorming, code structure review, debugging, and understanding implementation issues. The final application was not generated automatically: all AI outputs were reviewed, tested, and adapted by the authors before being included in the project.

See `AI_USAGE.md` for the full AI usage statement.

---

## Project structure

* `./modules/`
* `./Report.docx`
* `./demo_video.mp4`
* `./Transformation report example file`
* `./AI_USAGE.md`
* `./sample_data/`
* `./app.py`
* `./README.md`
* `./requirements.txt`

---

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Deployed version link

here will be link
