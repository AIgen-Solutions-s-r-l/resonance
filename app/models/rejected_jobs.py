from sqlalchemy import Column, Integer, String, DateTime, PrimaryKeyConstraint, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class RejectedJob(Base):
    __tablename__ = "rejected_jobs"

    user_id = Column(Integer, nullable=False)
    job_id = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "job_id", name="pk_rejected_jobs"),
    )
