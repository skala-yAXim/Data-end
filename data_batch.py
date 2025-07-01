import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from app.rdb.client import get_db
from app.pipeline.github_pipeline import save_github_data
from app.pipeline.email_pipeline import save_all_email_data
from app.pipeline.docs_pipeline import save_docs_data
from app.pipeline.teams_post_pipeline import save_teams_posts_data
from app.common.statics_report import save_user_activities_to_rdb


def get_db_session() -> Session:
    db_gen = get_db()
    return next(db_gen)


# 매일 자정에 실행될 작업
async def run_batch():
    db = get_db_session()
    date = datetime.now() - timedelta(days=1)
    print(f"\n=== 배치 작업 시작: {datetime.now()} ===")
    try:
        print("GitHub 데이터 저장 시작...")
        await save_github_data(db, date)
        print("GitHub 데이터 저장 완료")

        print("이메일 데이터 저장 시작...")
        await save_all_email_data(db, date)
        print("이메일 데이터 저장 완료")

        print("Docs 데이터 저장 시작...")
        await save_docs_data(db, date)
        print("Docs 데이터 저장 완료")

        print("Teams 포스트 데이터 저장 시작...")
        await save_teams_posts_data(db, date)
        print("Teams 포스트 데이터 저장 완료")

        print(f"=== 모든 배치 작업 완료: {datetime.now()} ===\n")
    except Exception as e:
        print(f"에러 발생: {e}")
    finally:
        db.close()


# 매주 월요일 자정에 실행될 작업
async def run_user_activity_report():
    db = get_db_session()
    date_str = datetime.now().strftime("%Y-%m-%d")
    try:
        print(f"=== 업무 통계 저장 시작: {date_str} ===")
        save_user_activities_to_rdb(date_str, db)
        print("업무 통계 저장 완료")
    except Exception as e:
        print(f"save_user_activities_to_rdb 오류 발생: {e}")
    finally:
        db.close()


async def run_all_jobs_for_friday():
    await run_batch()
    await run_user_activity_report()


# APScheduler 설정
scheduler = BlockingScheduler(timezone=ZoneInfo("Asia/Seoul"))

# 매일 자정 (00:00)에 실행
# 목~토 자정에는 run_batch만 실행
scheduler.add_job(lambda: asyncio.run(run_batch()), 'cron', day_of_week='sat,sun,mon,tue,wed,thu', hour=0, minute=0)

# 금요일 자정에는 run_batch → 통계 보고까지 함께 실행
scheduler.add_job(lambda: asyncio.run(run_all_jobs_for_friday()), 'cron', day_of_week='fri', hour=0, minute=0)


if __name__ == '__main__':
    print("✅ 스케줄러가 시작되었습니다.")
    scheduler.start()