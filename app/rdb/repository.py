from sqlalchemy.orm import Session
from app.rdb.schema import Team, User, TeamMember, GitInfo

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
