import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from backend.app.config import settings

# Engine setup with thread-safe settings for SQLite
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class DBAnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    id = Column(String, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    status = Column(String, default="pending", index=True)
    progress_pct = Column(Integer, default=0)
    current_agent = Column(String, nullable=True)
    current_step = Column(String, nullable=True)
    llm_provider_used = Column(String, default="local_fallback")
    tokens_consumed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = Column(Text, nullable=True)
    
    # Store JSON payloads for complex nested structures (charts, quality, report)
    charts_json = Column(Text, default="[]")
    quality_json = Column(Text, default="[]")
    report_json = Column(Text, nullable=True)

    logs = relationship("DBAgentLog", back_populates="session", cascade="all, delete-orphan", order_by="DBAgentLog.timestamp")

class DBAgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("analysis_sessions.id"), index=True)
    agent = Column(String, nullable=False)
    step_type = Column(String, nullable=False) # thought, action, observation, etc.
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    tool_name = Column(String, nullable=True)
    tool_input_json = Column(Text, nullable=True)
    tool_output_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    session = relationship("DBAnalysisSession", back_populates="logs")

def init_db():
    if "sqlite" in settings.DATABASE_URL:
        # Ensure parent directory exists for SQLite database file
        db_path = settings.DATABASE_URL.replace("sqlite:////", "/").replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception:
                pass
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
