from typing import Optional
from sqlalchemy.orm import Session
from app.rdb.schema import Team, User, TeamMember, GitInfo, DailyUserActivity

# 모든 팀 조회
def find_all_teams(db: Session) -> list[Team]:
    return db.query(Team).all()

# 모든 사용자 조회
def find_all_users(db: Session) -> list[User]:
    return db.query(User).all()

# 모든 팀 멤버 조회
def find_all_team_members(db: Session) -> list[TeamMember]:
    return db.query(TeamMember).all()

def find_all_git_info(db: Session) -> list[GitInfo]:
    return db.query(GitInfo).all()

def save_daily_user_activity(activity: DailyUserActivity, db: Session):
    db.add(activity)
    db.commit()

def flush_daily_user_activity_if_exists(db: Session):
    exists = db.query(DailyUserActivity).first() is not None

    if exists:
        db.query(DailyUserActivity).delete()
        db.commit()

def delete_all_daily_user_activities(db: Session):
    db.query(DailyUserActivity).delete()
    db.commit()