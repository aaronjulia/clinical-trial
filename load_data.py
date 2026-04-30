import pandas as pd

from base import Base
from db import CELL_COLUMNS, CSV_PATH, SessionLocal, engine
from schema import Cells, Projects, Samples, Subjects


REQUIRED_COLUMNS = [
    "project",
    "subject",
    "condition",
    "age",
    "sex",
    "treatment",
    "response",
    "sample",
    "sample_type",
    "time_from_treatment_start",
    *CELL_COLUMNS,
]


def read_source_data() -> pd.DataFrame:
    """Read and validate the source CSV before loading it into SQLite."""
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"cell-count.csv is missing required columns: {missing_columns}")

    return df


def load_data() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    df = read_source_data()

    projects = (
        df[["project"]]
        .drop_duplicates()
        .rename(columns={"project": "project_id"})
        .to_dict(orient="records")
    )
    subjects = (
        df[["subject", "project", "age", "sex", "response", "condition", "treatment"]]
        .drop_duplicates()
        .rename(columns={"subject": "subject_id", "project": "project_id"})
        .to_dict(orient="records")
    )
    samples = (
        df[["sample", "subject", "sample_type", "time_from_treatment_start"]]
        .drop_duplicates()
        .rename(
            columns={
                "sample": "sample_id",
                "subject": "subject_id",
                "time_from_treatment_start": "time_from_treatment",
            }
        )
        .to_dict(orient="records")
    )
    cells = (
        df.melt(
            id_vars=["sample"],
            value_vars=CELL_COLUMNS,
            var_name="cell_type",
            value_name="cell_count",
        )
        .rename(columns={"sample": "sample_id"})
        .to_dict(orient="records")
    )

    with SessionLocal() as session:
        session.execute(Projects.__table__.insert(), projects)
        session.execute(Subjects.__table__.insert(), subjects)
        session.execute(Samples.__table__.insert(), samples)
        session.execute(Cells.__table__.insert(), cells)
        session.commit()

    print(f"Loaded {len(samples):,} samples and {len(cells):,} cell-count records into {engine.url.database}")


if __name__ == "__main__":
    load_data()
