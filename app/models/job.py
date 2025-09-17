from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Text,
    UniqueConstraint,
    Float,
)
from sqlalchemy.orm import relationship, declarative_base, Mapped
from pgvector.sqlalchemy import Vector
from uuid import uuid4
from typing import List, Optional

from app.models.classes import Base


class Company(Base):
    __tablename__ = "Companies"

    company_id: int = Column(Integer, primary_key=True, autoincrement=True)
    company_name: str = Column(String, nullable=False)
    logo: Optional[str] = Column(String, nullable=True)

    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="company")


class Country(Base):
    __tablename__ = "Countries"

    country_id: int = Column(Integer, primary_key=True, autoincrement=True)
    country_name: str = Column(String, nullable=False)


class Location(Base):
    __tablename__ = "Locations"

    location_id: int = Column(Integer, primary_key=True, autoincrement=True)
    city: str = Column(String, nullable=False)
    latitude: Optional[float] = Column(Float, nullable=True)
    longitude: Optional[float] = Column(Float, nullable=True)

    country: int = Column(Integer, ForeignKey("Countries.country_id"), nullable=False)

    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="location")


class Job(Base):
    __tablename__ = "Jobs"

    id: str = Column(String, primary_key=True, default=lambda: str(uuid4()))
    title: str = Column(String, nullable=False)
    workplace_type: Optional[str] = Column(String)
    posted_date: Optional[DateTime] = Column(DateTime)
    job_state: Optional[str] = Column(String)
    description: Optional[str] = Column(Text)
    short_description: Optional[str] = Column(Text)
    field: Optional[str] = Column(String)
    experience: Optional[str] = Column(String(255))
    skills_required: Optional[str] = Column(Text)
    apply_link: Optional[str] = Column(String)
    embedding: Optional[Vector] = Column(Vector)
    sparse_embeddings: Optional[Vector] = Column(Vector)
    cluster_id: Optional[int] = Column(Integer)
    portal: Optional[str] = Column(String)

    company_id: int = Column(
        Integer, ForeignKey("Companies.company_id"), nullable=False
    )
    location_id: int = Column(
        Integer, ForeignKey("Locations.location_id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "location_id", "apply_link", name="unique_location_apply_link"
        ),
    )

    company: Mapped["Company"] = relationship("Company", back_populates="jobs")
    location: Mapped["Location"] = relationship("Location", back_populates="jobs")
