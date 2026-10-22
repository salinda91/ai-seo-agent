from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from ..core.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Website(Base):
    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    cms_type = Column(String(50), default="wordpress")  # wordpress, woocommerce, laravel, custom
    admin_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    gsc_property_id = Column(String(255), nullable=True)
    gsc_verified = Column(Boolean, default=False)
    automation_mode = Column(String(50), default="supervised")  # recommendation, supervised, autonomous
    local_repo_path = Column(String(500), nullable=True)  # path to local project folder for non-WordPress auto-fix & git push
    git_branch = Column(String(100), default="main")
    git_remote = Column(String(100), default="origin")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tasks = relationship("Task", back_populates="website", cascade="all, delete-orphan")
    crawl_results = relationship("CrawlResult", back_populates="website", cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="website", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="website", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="website", cascade="all, delete-orphan")
    business_profile = relationship("BusinessProfile", back_populates="website", uselist=False, cascade="all, delete-orphan")

class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    website_id = Column(Integer, ForeignKey("websites.id"), unique=True, nullable=False, index=True)
    business_name = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    offerings = Column(JSON, default=list)  # list of products/services
    target_audience = Column(JSON, default=list)  # customer demographics/segments
    service_locations = Column(JSON, default=list)  # locations/markets
    languages = Column(JSON, default=list)  # ["en", ...]
    competitors = Column(JSON, default=list)  # competitor domains/names
    seo_goals = Column(JSON, default=list)  # primary SEO objectives
    content_gaps = Column(JSON, default=list)  # missing pages/topics
    internal_linking_plan = Column(JSON, default=list)  # semantic internal linking opportunities
    authority_roadmap = Column(JSON, default=list)  # outreach & authority building actions
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    website = relationship("Website", back_populates="business_profile")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False, index=True)
    task_type = Column(String(60), nullable=False, index=True)
    status = Column(String(50), default="pending", index=True)
    risk_level = Column(String(20), default="low")  # low, medium, high
    payload = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    screenshots = Column(JSON, default=list)  # list of screenshot paths/metadata
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    requires_human_approval = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    website = relationship("Website", back_populates="tasks")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False, index=True)
    task_id = Column(String(36), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    details = Column(JSON, default=dict)
    status = Column(String(30), default="success")  # success, warning, failure, paused
    created_at = Column(DateTime(timezone=True), default=utcnow)

    website = relationship("Website", back_populates="audit_logs")

class CrawlResult(Base):
    __tablename__ = "crawl_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False, index=True)
    url = Column(String(1000), nullable=False, index=True)
    status_code = Column(Integer, default=200)
    title = Column(String(500), nullable=True)
    meta_description = Column(Text, nullable=True)
    h1 = Column(Text, nullable=True)
    canonical = Column(String(1000), nullable=True)
    robots_meta = Column(String(255), nullable=True)
    internal_links_count = Column(Integer, default=0)
    external_links_count = Column(Integer, default=0)
    images_without_alt = Column(Integer, default=0)
    issues = Column(JSON, default=list)
    crawled_at = Column(DateTime(timezone=True), default=utcnow)

    website = relationship("Website", back_populates="crawl_results")

class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False, index=True)
    phrase = Column(String(255), nullable=False, index=True)
    target_page = Column(String(1000), nullable=True)
    search_intent = Column(String(50), default="informational")  # informational, transactional, commercial, navigational
    country = Column(String(10), default="US")
    language = Column(String(10), default="en")
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)
    position = Column(Float, default=0.0)
    opportunity_score = Column(Float, default=0.0)
    confidence = Column(Float, default=1.0)
    source = Column(String(50), default="gsc")  # gsc, crawl, gemini_ai
    research_date = Column(DateTime(timezone=True), default=utcnow)

    website = relationship("Website", back_populates="keywords")

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False, index=True)
    url = Column(String(1000), nullable=False)
    issue_title = Column(String(255), nullable=False)
    severity = Column(String(20), default="medium")  # critical, high, medium, low
    category = Column(String(50), default="onpage")  # technical, content, onpage, indexing
    evidence = Column(Text, nullable=True)
    proposed_fix = Column(Text, nullable=False)
    proposed_change_data = Column(JSON, default=dict)  # {"field": "meta_description", "new_value": "..."}
    expected_benefit = Column(Text, nullable=True)
    risk_level = Column(String(20), default="low")  # low, medium, high
    automation_eligible = Column(Boolean, default=True)
    status = Column(String(30), default="suggested")  # suggested, approved, rejected, applied
    created_at = Column(DateTime(timezone=True), default=utcnow)

    website = relationship("Website", back_populates="recommendations")

class ChangeRecord(Base):
    __tablename__ = "change_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False, index=True)
    recommendation_id = Column(Integer, nullable=True)
    url = Column(String(1000), nullable=False)
    field_name = Column(String(100), nullable=False)
    before_value = Column(Text, nullable=True)
    after_value = Column(Text, nullable=True)
    status = Column(String(30), default="pending")  # pending, applied, verified, rolled_back
    applied_at = Column(DateTime(timezone=True), default=utcnow)
    verified_at = Column(DateTime(timezone=True), nullable=True)
