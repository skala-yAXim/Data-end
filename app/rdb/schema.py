from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, CheckConstraint, TIMESTAMP, DateTime, Date
from sqlalchemy.orm import relationship
from app.rdb.client import Base
from sqlalchemy import Enum as SQLAlchemyEnum
import enum

class Weekday(enum.IntEnum):
    FRIDAY = 0
    SATURDAY = 1
    SUNDAY = 2
    MONDAY = 3
    TUESDAY = 4
    WEDNESDAY = 5
    THURSDAY = 6


class Team(Base):
    __tablename__ = "team"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    installation_id = Column(String)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    user_role = Column(String, nullable=False)
    active = Column(Boolean, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "user_role IN ('MEMBER', 'LEADER', 'USER', 'ADMIN')", name="users_user_role_check"
        ),
    )


class TeamMember(Base):
    __tablename__ = "team_member"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String)
    role = Column(String)
    team_id = Column(String, ForeignKey("team.id"))

    team = relationship("Team", lazy="select")

    __table_args__ = (
        CheckConstraint(
            "role IN ('MEMBER', 'LEADER', 'USER', 'ADMIN')", name="team_member_role_check"
        ),
    )


class GitInfo(Base):
    __tablename__ = "git_info"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    git_id = Column(String)
    git_email = Column(String)
    git_url = Column(String)
    avatar_url = Column(String)

    # 관계 설정 (양방향 관계를 원할 경우 users 모델에도 relationship 추가 필요)
    user = relationship("User", lazy="select")


class DailyUserActivity(Base):
    __tablename__ = "daily_user_activity"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    report_date = Column(Date, nullable=False)
    day = Column(SQLAlchemyEnum(Weekday, native_enum=False), nullable=False)
    teams_post = Column(Integer, nullable=False)
    email_send = Column(Integer, nullable=False)
    email_receive = Column(Integer, nullable=False)
    docs_docx = Column(Integer, nullable=False)
    docs_xlsx = Column(Integer, nullable=False)
    docs_txt = Column(Integer, nullable=False)
    docs_etc = Column(Integer, nullable=False)
    git_pull_request = Column(Integer, nullable=False)
    git_commit = Column(Integer, nullable=False)
    git_issue = Column(Integer, nullable=False)

    user = relationship("User", lazy="select")
