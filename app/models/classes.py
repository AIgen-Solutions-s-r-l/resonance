import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import (
    Column,
    Integer,
    PrimaryKeyConstraint,
    String,
    ForeignKey,
    DateTime,
    Text,
    UniqueConstraint,
    Float,
    Table,
)
from sqlalchemy.orm import relationship, declarative_base, Mapped
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from geoalchemy2 import Geometry
from typing import List, Optional

Base = declarative_base()


FieldJobs = Table(
    "FieldJobs",
    Base.metadata,
    Column("job_id", UUID(as_uuid=True), ForeignKey("Jobs.id", ondelete="CASCADE"), primary_key=True),
    Column("field_id", Integer, ForeignKey("Fields.id", ondelete="CASCADE"), primary_key=True),
)

class Field(Base):
    __tablename__ = "Fields"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    root_field: Mapped[str] = Column(String(255), nullable=False)
    sub_field: Mapped[str] = Column(String(255), nullable=False)
    record_creation_time: Mapped[Optional[DateTime]] = Column(
        DateTime(), server_default=func.now(), nullable=False
    )

    jobs: Mapped[List["Job"]] = relationship(
        "Job",
        secondary=FieldJobs,
        back_populates="fields"
    )


class Company(Base):
    __tablename__ = "Companies"

    company_id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = Column(String(255), nullable=False)
    logo: Mapped[Optional[str]] = Column(Text, nullable=True)
    record_creation_time: Mapped[Optional[DateTime]] = Column(
        DateTime(), server_default=func.now(), nullable=False
    )

    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="company")


class Country(Base):
    __tablename__ = "Countries"

    country_id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    country_name: Mapped[str] = Column(String(255), nullable=False)
    record_creation_time: Mapped[Optional[DateTime]] = Column(
        DateTime(), server_default=func.now(), nullable=False
    )


class Location(Base):
    __tablename__ = "Locations"

    location_id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    city: Mapped[str] = Column(String(255), nullable=False)
    latitude: Mapped[Optional[float]] = Column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = Column(Float, nullable=True)
    geom: Mapped[Optional[Geometry]] = Column(Geometry("POINT"), nullable=True)
    record_creation_time: Mapped[Optional[DateTime]] = Column(
        DateTime(), server_default=func.now(), nullable=False
    )

    country: Mapped[int] = Column(
        Integer, ForeignKey("Countries.country_id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("city", "country", name="unique_location_city_country"),
    )

    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="location")


class Job(Base):
    __tablename__ = "Jobs"

    id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = Column(String(255), nullable=False)
    workplace_type: Mapped[Optional[str]] = Column(String(10))
    posted_date: Mapped[Optional[DateTime]] = Column(DateTime)
    job_state: Mapped[Optional[str]] = Column(String(8))
    description: Mapped[Optional[str]] = Column(Text)
    short_description: Mapped[Optional[str]] = Column(Text)
    experience: Mapped[Optional[str]] = Column(String(255))
    skills_required: Mapped[Optional[str]] = Column(Text)
    apply_link: Mapped[Optional[str]] = Column(Text)
    embedding: Mapped[Optional[Vector]] = Column(Vector)
    portal: Mapped[Optional[str]] = Column(String(255))
    record_creation_time: Mapped[Optional[DateTime]] = Column(
        DateTime(), server_default=func.now(), nullable=False
    )

    company_id: Mapped[int] = Column(
        Integer, ForeignKey("Companies.company_id"), nullable=False
    )
    location_id: Mapped[int] = Column(
        Integer, ForeignKey("Locations.location_id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "location_id", "apply_link", name="unique_location_apply_link"
        ),
    )

    company: Mapped["Company"] = relationship("Company", back_populates="jobs")
    location: Mapped["Location"] = relationship("Location", back_populates="jobs")


class RejectedJob(Base):
    __tablename__ = "rejected_jobs"

    user_id = Column(Integer, nullable=False)
    job_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), ForeignKey("Jobs.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "job_id", name="pk_rejected_jobs"),
    )
