import asyncio
from datetime import datetime, timedelta
from app.vectordb.client import flush_all_collections
from apscheduler.schedulers.blocking import BlockingScheduler
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

import os
import aiohttp
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

        # AI API 호출 (배치 완료 알림)
        print("AI API 호출 시작...")
        await create_daily_report()
        print("AI API 호출 완료")

        print(f"=== 모든 daily 배치 작업 완료: {datetime.now()} ===\n")
    except Exception as e:
        print(f"에러 발생: {e}")
    finally:
        db.close()


# 토요일 자정에 실행될 작업
async def run_batch_with_flush():
    await flush_all_collections()
    await run_batch()
    print(f"=== 토요일 배치 작업 완료: {datetime.now()} ===\n")


# 금요일 자정에 실행될 작업
async def run_user_activity_report():
    db = get_db_session()
    date_str = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
    try:
        print(f"=== 업무 통계 저장 시작: {date_str} ===")
        save_user_activities_to_rdb(date_str, db)
        print("=== 업무 통계 저장 완료 ===")
    except Exception as e:
        print(f"save_user_activities_to_rdb 오류 발생: {e}")
    finally:
        db.close()


async def run_all_jobs_for_friday():
    await run_batch()
    await run_user_activity_report()
    await create_weekly_report()
    await create_team_weekly_report()
    print(f"=== 금요일 배치 작업 완료: {datetime.now()} ===\n")
    

async def create_daily_report():
    await call_ai_api("daily")
    print("daily 생성 완료")


async def create_weekly_report():
    await call_ai_api("weekly")
    print("weekly 생성 완료")


async def create_team_weekly_report():
    await call_ai_api("team-weekly")
    print("team-weekly 생성 완료")


async def call_ai_api(endpoint: str = ""):
    """AI API 호출 함수"""
    api_base_url = os.environ.get('AI_API_BASE_URL')
    
    if not api_base_url:
        print("경고: AI_API_BASE_URL 환경변수가 설정되지 않았습니다.")
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{api_base_url}/{endpoint}",
                json={
                    "status": "completed",
                    "timestamp": datetime.now().isoformat(),
                    "message": "배치 작업이 성공적으로 완료되었습니다."
                },
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status != 200:
                    print(f"AI API 호출 실패 - 상태코드: {response.status}")
    except Exception as e:
        print(f"AI API 호출 중 에러 발생: {e}")


# APScheduler 설정
scheduler = BlockingScheduler(timezone=ZoneInfo("Asia/Seoul"))

# 매일 자정 (00:00)에 실행
# 일~목 자정에는 run_batch만 실행
scheduler.add_job(lambda: asyncio.run(run_batch()), 'cron', day_of_week='sun,mon,tue,wed,thu', hour=0, minute=0)

# 토요일 자정에는 flush 후 run_batch 실행
scheduler.add_job(lambda: asyncio.run(run_batch_with_flush()), 'cron', day_of_week='sat', hour=0, minute=0)

# 금요일 자정에는 run_batch → 통계 보고까지 함께 실행
scheduler.add_job(lambda: asyncio.run(run_all_jobs_for_friday()), 'cron', day_of_week=' fri', hour=0, minute=0)


if __name__ == '__main__':
    print("✅ 스케줄러가 시작되었습니다.")
    scheduler.start()