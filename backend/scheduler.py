#!/usr/bin/env python3
"""
Job Management System - Cron Scheduler
DB에 저장된 cron 스케줄을 실행하는 백그라운드 서비스
"""

import time
import os
import sys
import subprocess
from datetime import datetime
from croniter import croniter
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pytz

# 한국 시간대
KST = pytz.timezone('Asia/Seoul')

# DB 연결 (독립적인 연결)
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3340/job_management")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3340/job_management")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_active_schedules():
    """활성화된 스케줄 목록 조회"""
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT s.schedule_id, s.job_id, s.cron_expression, j.name, j.docker_image
                FROM JobSchedules s
                JOIN Jobs j ON s.job_id = j.job_id
                WHERE s.is_active = TRUE
            """)
        ).fetchall()
        return result
    finally:
        db.close()

def should_run_now(cron_expression, last_run=None):
    """현재 시간에 실행해야 하는지 확인"""
    now = datetime.now(KST)
    cron = croniter(cron_expression, now)
    
    # 다음 실행 시간이 현재 시간으로부터 1분 이내인지 확인
    next_run = cron.get_next(datetime)
    time_diff = (next_run - now).total_seconds()
    
    return 0 <= time_diff <= 60

def execute_job(job_id, job_name, docker_image):
    """Job 실행"""
    db = SessionLocal()
    try:
        print(f"🚀 Executing scheduled job: {job_name}")
        
        # JobRun 기록 생성
        run_id = f"sched-{int(time.time())}"
        kst_now = datetime.now(KST)
        
        db.execute(
            text("""
                INSERT INTO JobRuns (run_id, job_id, run_type_id, status, started_at)
                VALUES (:run_id, :job_id, 
                        (SELECT run_type_id FROM RunTypes WHERE name = 'SCHEDULED' LIMIT 1),
                        'RUNNING', :started_at)
            """),
            {"run_id": run_id, "job_id": job_id, "started_at": kst_now}
        )
        
        # Docker 컨테이너 시작 (동기 실행으로 완료까지 대기)
        if docker_image:
            container_name = f"scheduled-{job_name}-{int(time.time())}"
            result = subprocess.run(
                ["docker", "run", "--rm", "--name", container_name, docker_image],
                capture_output=True, text=True
            )
            
            exit_code = result.returncode
            print(f"🐳 Container {container_name} completed with exit code: {exit_code}")
            
            # 실행 완료 처리
            status = "SUCCESS" if exit_code == 0 else "FAILED"
            db.execute(
                text("UPDATE JobRuns SET status = :status, finished_at = :finished_at WHERE run_id = :run_id"),
                {"status": status, "finished_at": datetime.now(KST), "run_id": run_id}
            )
            
            # 완료 audit log 생성
            db.execute(
                text("""
                    INSERT INTO AuditLogs (user_id, action_type, target_type, target_id, after_value)
                    VALUES ((SELECT user_id FROM Users WHERE username = 'system' LIMIT 1),
                            'CONTAINER_LOGS', 'job', :job_id, 
                            JSON_OBJECT('container_name', :container_name, 'status', :status, 'exit_code', :exit_code, 'logs', :logs))
                """),
                {"job_id": job_id, "container_name": container_name, "status": status, "exit_code": exit_code, "logs": result.stdout + result.stderr}
            )
            
            print(f"✅ Job {job_name} completed: {status}")
        else:
            print(f"⚠️ No docker image specified for {job_name}")
        
        db.commit()
        
    except Exception as e:
        print(f"❌ Error executing job {job_name}: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """메인 스케줄러 루프"""
    print("🕐 Job Scheduler started")
    print(f"📅 Current time: {datetime.now(KST)}")
    
    last_check = {}  # 마지막 실행 시간 추적
    
    while True:
        try:
            schedules = get_active_schedules()
            current_time = datetime.now(KST)
            print(f"🔍 Checking {len(schedules)} schedules at {current_time.strftime('%H:%M:%S')}")
            
            for schedule in schedules:
                schedule_id, job_id, cron_expr, job_name, docker_image = schedule
                
                # 1분마다 한 번만 체크하도록 제한
                last_run = last_check.get(schedule_id)
                if last_run and (current_time - last_run).total_seconds() < 60:
                    continue
                
                if should_run_now(cron_expr, last_run):
                    print(f"⏰ Schedule triggered: {job_name} ({cron_expr})")
                    execute_job(job_id, job_name, docker_image)
                    last_check[schedule_id] = current_time
            
            # 30초마다 체크
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n🛑 Scheduler stopped by user")
            break
        except Exception as e:
            print(f"❌ Scheduler error: {e}")
            time.sleep(60)  # 오류 시 1분 대기

if __name__ == "__main__":
    main()
