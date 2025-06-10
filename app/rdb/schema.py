from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, CheckConstraint, TIMESTAMP, DateTime
from sqlalchemy.orm import relationship
from app.rdb.client import Base

class Team(Base):
    __tablename__ = "team"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    installation_id = Column(String)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)

    members = relationship("TeamMember", back_populates="team")


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

    team = relationship("Team", back_populates="members")

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
