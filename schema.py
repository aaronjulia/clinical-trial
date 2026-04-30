from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from base import Base


class Projects(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(50), primary_key=True)


class Subjects(Base):
    __tablename__ = "subjects"
    __table_args__ = (
        Index("ix_subjects_condition_treatment_response", "condition", "treatment", "response"),
        Index("ix_subjects_project", "project_id"),
    )

    subject_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("projects.project_id"), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    sex: Mapped[str] = mapped_column(String(50), nullable=False)
    response: Mapped[str] = mapped_column(String(50), nullable=True)
    condition: Mapped[str] = mapped_column(String(50), nullable=False)
    treatment: Mapped[str] = mapped_column(String(50), nullable=False)


class Samples(Base):
    __tablename__ = "samples"
    __table_args__ = (
        Index("ix_samples_subject", "subject_id"),
        Index("ix_samples_type_time", "sample_type", "time_from_treatment"),
    )

    sample_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(50), ForeignKey("subjects.subject_id"), nullable=False)
    sample_type: Mapped[str] = mapped_column(String(50), nullable=False)
    time_from_treatment: Mapped[int] = mapped_column(Integer, nullable=False)


class Cells(Base):
    __tablename__ = "cells"
    __table_args__ = (Index("ix_cells_cell_type", "cell_type"),)

    sample_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("samples.sample_id"),
        primary_key=True,
    )
    cell_type: Mapped[str] = mapped_column(String(50), primary_key=True)
    cell_count: Mapped[int] = mapped_column(Integer, nullable=False)
