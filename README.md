
## Run Instructions

Install dependencies:

```bash
make setup
```

Run the full pipeline:

```bash
make pipeline
```

Start the dashboard:

```bash
make dashboard
```

Dashboard link: http://localhost:8501



The generated SQLite database is `cell_trial.db` in the repository root. It is ignored by Git because `python load_data.py` recreates it deterministically.

## Schema

The SQLite schema is normalized into four tables:

- `projects`: one row per project.
- `subjects`: one row per subject with project, age, sex, response, condition, and treatment.
- `samples`: one row per biological sample with subject, sample type, and time from treatment start.
- `cells`: long-form cell counts keyed by `(sample_id, cell_type)`.

This design gives the database a good heiriearchy and scalability. Keeping only data that belongs to each entitiy within each table. Whats good about the cell taba is that its just a row of sample id, cell_type, and the count so it gives you the ability to add any kind of cell from any sample without changing anything.


## Code Structure

The code structure was kept flat at the root as some of the files and outputs needed to stay within the root. Doing so it kept everything simple.

- `load_data.py`: validates `cell-count.csv`, initializes SQLite, and loads all projects, subjects, samples, and cell counts.
- `schema.py`: SQLAlchemy table definitions and indexes.
- `db.py`: shared database path, SQLAlchemy engine, and cell population constants.
- `analysis.py`: Part 2 through Part 4 analysis functions and output generation.
- `dashboard.py`: Streamlit dashboard that displays the generated outputs and supports interactive filtering.
- `Makefile`: grading entry points for setup, pipeline execution, and dashboard launch.
