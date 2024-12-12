from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import pytz
import json
import os

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

app = FastAPI(title="Job Management System - Auto Tracking")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 연결
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@mysql:3306/job_management")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic 모델
class AutoJobRegister(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    script_path: Optional[str] = None
    function_name: Optional[str] = None
    container_id: Optional[str] = None
    container_name: Optional[str] = None
    image: Optional[str] = None
    user: str
    hostname: str
    pid: Optional[int] = None
    cwd: Optional[str] = None
    started_at: str
    environment: Optional[Dict[str, Any]] = None

class JobScheduleCreate(BaseModel):
    job_id: str
    cron_expression: str
    is_active: Optional[bool] = True

class JobCompletion(BaseModel):
    status: str  # SUCCESS, FAILED, CANCELLED
    finished_at: str
    exit_code: Optional[int] = None
    result: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    logs: Optional[str] = None

class AuditLogCreate(BaseModel):
    user: str
    action_type: str
    target_type: str
    target_id: str
    details: Optional[Dict[str, Any]] = None

@app.post("/api/jobs/auto-register")
def auto_register_job(job_data: AutoJobRegister, db: Session = Depends(get_db)):
    """라이브러리에서 자동으로 Job을 등록"""
    try:
        # Job 유형 확인/생성
        type_result = db.execute(
            text("SELECT type_id FROM JobTypes WHERE name = :type_name"),
            {"type_name": job_data.type}
        ).fetchone()
        
        if not type_result:
            # 새로운 Job 유형 자동 생성
            type_id = str(uuid.uuid4())
            db.execute(
                text("INSERT INTO JobTypes (type_id, name, description) VALUES (:type_id, :name, :desc)"),
                {"type_id": type_id, "name": job_data.type, "desc": f"Auto-created type: {job_data.type}"}
            )
        else:
            type_id = type_result[0]
        
        # 사용자 확인/생성
        user_result = db.execute(
            text("SELECT user_id FROM Users WHERE username = :username"),
            {"username": job_data.user}
        ).fetchone()
        
        if not user_result:
            # 새로운 사용자 자동 생성
            user_id = str(uuid.uuid4())
            db.execute(
                text("""
                    INSERT INTO Users (user_id, username, email, role) 
                    VALUES (:user_id, :username, :email, 'developer')
                """),
                {
                    "user_id": user_id, 
                    "username": job_data.user,
                    "email": f"{job_data.user}@auto-detected.local"
                }
            )
        else:
            user_id = user_result[0]
        
        # Job 확인/생성 (같은 이름의 Job이 없으면 생성)
        job_result = db.execute(
            text("SELECT job_id FROM Jobs WHERE name = :name AND owner_id = :owner_id"),
            {"name": job_data.name, "owner_id": user_id}
        ).fetchone()
        
        if not job_result:
            # 새로운 Job 자동 생성
            job_id = str(uuid.uuid4())
            db.execute(
                text("""
                    INSERT INTO Jobs (job_id, name, description, type_id, owner_id, script_path, docker_image)
                    VALUES (:job_id, :name, :description, :type_id, :owner_id, :script_path, :docker_image)
                """),
                {
                    "job_id": job_id,
                    "name": job_data.name,
                    "description": job_data.description,
                    "type_id": type_id,
                    "owner_id": user_id,
                    "script_path": job_data.script_path,
                    "docker_image": job_data.image
                }
            )
        else:
            job_id = job_result[0]
        
        # 에이전트 확인/생성
        agent_result = db.execute(
            text("SELECT agent_id FROM Agents WHERE name = :hostname"),
            {"hostname": job_data.hostname}
        ).fetchone()
        
        if not agent_result:
            # 새로운 에이전트 자동 생성
            agent_id = str(uuid.uuid4())
            env_type_result = db.execute(
                text("SELECT env_type_id FROM EnvironmentTypes WHERE name = 'DOCKER'")
            ).fetchone()
            
            db.execute(
                text("""
                    INSERT INTO Agents (agent_id, name, hostname, env_type_id)
                    VALUES (:agent_id, :name, :hostname, :env_type_id)
                """),
                {
                    "agent_id": agent_id,
                    "name": f"auto-{job_data.hostname}",
                    "hostname": job_data.hostname,
                    "env_type_id": env_type_result[0]
                }
            )
        else:
            agent_id = agent_result[0]
        
        # RunType 조회 (MONITORED for auto-detected containers)
        run_type_result = db.execute(
            text("SELECT run_type_id FROM RunTypes WHERE name = 'MONITORED'")
        ).fetchone()
        
        if not run_type_result:
            raise HTTPException(status_code=500, detail="MONITORED run type not found")
        
        # JobRun 생성
        run_id = str(uuid.uuid4())
        db.execute(
            text("""
                INSERT INTO JobRuns (run_id, job_id, agent_id, run_type_id, 
                                   triggered_by_user_id, status, started_at)
                VALUES (:run_id, :job_id, :agent_id, :run_type_id, 
                       :user_id, 'RUNNING', :started_at)
            """),
            {
                "run_id": run_id,
                "job_id": job_id,
                "agent_id": agent_id,
                "run_type_id": run_type_result[0],
                "user_id": user_id,
                "started_at": datetime.fromisoformat(job_data.started_at.replace('Z', '+00:00'))
            }
        )
        
        db.commit()
        
        return {
            "run_id": run_id,
            "job_id": job_id,
            "message": "Job automatically registered and started tracking"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Auto registration failed: {str(e)}")

@app.put("/api/runs/{run_id}/complete")
def complete_job_run(run_id: str, completion: JobCompletion, db: Session = Depends(get_db)):
    """Job 실행 완료 처리"""
    try:
        # JobRun 업데이트
        db.execute(
            text("""
                UPDATE JobRuns 
                SET status = :status, exit_code = :exit_code, finished_at = :finished_at
                WHERE run_id = :run_id
            """),
            {
                "run_id": run_id,
                "status": completion.status,
                "exit_code": completion.exit_code,
                "finished_at": datetime.fromisoformat(completion.finished_at.replace('Z', '+00:00'))
            }
        )
        
        # 로그 저장 (있는 경우)
        if completion.logs:
            db.execute(
                text("""
                    INSERT INTO JobRunLogs (run_id, log_text)
                    VALUES (:run_id, :log_text)
                """),
                {"run_id": run_id, "log_text": completion.logs}
            )
        
        # 오류 저장 (있는 경우)
        if completion.error and completion.status == "FAILED":
            error_type_result = db.execute(
                text("SELECT error_type_id FROM ErrorTypes WHERE name = 'SCRIPT_ERROR'")
            ).fetchone()
            
            db.execute(
                text("""
                    INSERT INTO JobRunErrors (run_id, error_type_id, message, stacktrace)
                    VALUES (:run_id, :error_type_id, :message, :stacktrace)
                """),
                {
                    "run_id": run_id,
                    "error_type_id": error_type_result[0],
                    "message": completion.error.split('\n')[0][:500],  # 첫 줄만 메시지로
                    "stacktrace": completion.error
                }
            )
        
        db.commit()
        
        return {"message": "Job completion recorded successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to record completion: {str(e)}")

# 기존 API들도 유지
@app.get("/api/containers")
def get_containers(db: Session = Depends(get_db)):
    import subprocess
    
    # 로컬 docker ps -a로 모든 컨테이너 조회 및 DB 업데이트
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}\t{{.ID}}\t{{.Image}}"],
            capture_output=True, text=True, check=True
        )
        
        containers = {}
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 4:
                    name, status, container_id, image = parts
                    
                    # 상태 정확히 판단
                    if status.startswith('Up'):
                        container_status = "RUNNING"
                        is_active = True
                    elif status.startswith('Exited'):
                        container_status = "STOPPED"
                        is_active = False
                    elif status.startswith('Created'):
                        container_status = "CREATED"
                        is_active = False
                    else:
                        container_status = "UNKNOWN"
                        is_active = False
                    
                    # DB에 컨테이너 정보 업데이트/삽입
                    db.execute(
                        text("""
                        INSERT INTO Jobs (job_id, name, description, type_id, owner_id, docker_image, is_active, created_at)
                        SELECT UUID(), :name, :description, 
                               (SELECT type_id FROM JobTypes WHERE name = 'CONTAINER' LIMIT 1),
                               (SELECT user_id FROM Users WHERE username = 'system' LIMIT 1),
                               :docker_image, :is_active, NOW()
                        WHERE NOT EXISTS (SELECT 1 FROM Jobs WHERE name = :name)
                        """),
                        {
                            "name": name,
                            "description": f"Auto-detected container: {image}",
                            "docker_image": image,
                            "is_active": is_active
                        }
                    )
                    
                    # 기존 job의 상태와 이미지 업데이트
                    db.execute(
                        text("UPDATE Jobs SET is_active = :is_active, docker_image = :docker_image WHERE name = :name"),
                        {"is_active": is_active, "docker_image": image, "name": name}
                    )
                    
                    containers[name] = {
                        "name": name,
                        "status": container_status,
                        "container_id": container_id,
                        "image": image
                    }
        
        db.commit()
    except Exception as e:
        print(f"Docker sync error: {e}")
        containers = {}
    
    # DB에서 job 정보 조회
    result = db.execute(
        text("""
            SELECT j.job_id, j.name, j.description, jt.name as type_name,
                   u.username, j.is_active, j.created_at
            FROM Jobs j
            JOIN JobTypes jt ON j.type_id = jt.type_id
            LEFT JOIN Users u ON j.owner_id = u.user_id
            ORDER BY j.created_at DESC
        """)
    ).fetchall()
    
    # NOT_FOUND 상태인 Job들을 수집하고 제거
    jobs_to_remove = []
    result_list = []
    
    for row in result:
        container_status = containers.get(row[1], {}).get("status", "NOT_FOUND")
        
        if container_status == "NOT_FOUND":
            jobs_to_remove.append(row[0])  # job_id 수집
        else:
            result_list.append({
                "job_id": row[0],
                "name": row[1], 
                "description": row[2],
                "type_name": row[3],
                "username": row[4],
                "is_active": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "container_status": container_status,
                "container_id": containers.get(row[1], {}).get("container_id", None),
                "docker_image": containers.get(row[1], {}).get("image", "N/A")
            })
    
    # NOT_FOUND Job들 제거
    if jobs_to_remove:
        for job_id in jobs_to_remove:
            try:
                # 관련 데이터 순서대로 삭제
                db.execute(text("DELETE FROM JobRunErrors WHERE run_id IN (SELECT run_id FROM JobRuns WHERE job_id = :job_id)"), {"job_id": job_id})
                db.execute(text("DELETE FROM JobRunLogs WHERE run_id IN (SELECT run_id FROM JobRuns WHERE job_id = :job_id)"), {"job_id": job_id})
                db.execute(text("DELETE FROM JobRuns WHERE job_id = :job_id"), {"job_id": job_id})
                db.execute(text("DELETE FROM JobSchedules WHERE job_id = :job_id"), {"job_id": job_id})
                db.execute(text("DELETE FROM Jobs WHERE job_id = :job_id"), {"job_id": job_id})
                
                # 감사 로그 기록
                db.execute(text("""
                    INSERT INTO AuditLogs (user_id, action_type, target_type, target_id, before_value)
                    VALUES ((SELECT user_id FROM Users WHERE username = 'system' LIMIT 1), 
                            'AUTO_DELETE', 'job', :job_id, JSON_OBJECT('reason', 'Container not found'))
                """), {"job_id": job_id})
                
                print(f"🗑️ Auto-removed job {job_id} (container not found)")
            except Exception as e:
                print(f"❌ Error removing job {job_id}: {e}")
        
        db.commit()
    
    return result_list

@app.get("/api/containers/{job_id}/latest-run")
def get_latest_run(job_id: str, db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            SELECT jr.run_id, jr.status, jr.started_at, jr.finished_at, 
                   u.username, rt.name as run_type
            FROM JobRuns jr
            LEFT JOIN Users u ON jr.triggered_by_user_id = u.user_id
            LEFT JOIN RunTypes rt ON jr.run_type_id = rt.run_type_id
            WHERE jr.job_id = :job_id
            ORDER BY jr.started_at DESC
            LIMIT 1
        """),
        {"job_id": job_id}
    ).fetchone()
    
    if not result:
        return {"message": "No execution history found"}
    
    return {
        "run_id": result[0],
        "status": result[1],
        "started_at": result[2].isoformat() if result[2] else None,
        "finished_at": result[3].isoformat() if result[3] else None,
        "user": result[4] or "System",
        "run_type": result[5] or "UNKNOWN"
    }

@app.get("/api/jobs")
def get_jobs(db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            SELECT j.job_id, j.name, j.description, jt.name as type_name,
                   u.username, j.is_active, j.created_at, j.docker_image
            FROM Jobs j
            JOIN JobTypes jt ON j.type_id = jt.type_id
            LEFT JOIN Users u ON j.owner_id = u.user_id
            ORDER BY j.created_at DESC
        """)
    ).fetchall()
    
    return [
        {
            "job_id": row[0],
            "name": row[1],
            "description": row[2],
            "type_name": row[3],
            "owner_username": row[4] or "Unknown",
            "is_active": row[5],
            "created_at": row[6].isoformat() if row[6] else None,
            "docker_image": row[7]
        }
        for row in result
    ]

@app.post("/api/containers/{job_id}/start")
def start_container(job_id: str, db: Session = Depends(get_db)):
    """컨테이너 시작"""
    try:
        import subprocess
        
        # job_id로 컨테이너 정보 조회
        result = db.execute(
            text("SELECT name, docker_image FROM Jobs WHERE job_id = :job_id"),
            {"job_id": job_id}
        ).fetchone()
        
        if not result:
            return {"error": "Container not found", "success": False}
        
        container_name, docker_image = result
        
        # 기존 컨테이너 상태 확인
        inspect_result = subprocess.run(
            ["docker", "inspect", container_name], 
            capture_output=True, text=True
        )
        
        if inspect_result.returncode == 0:
            # 컨테이너가 존재하는 경우 - 상태 확인
            import json
            container_info = json.loads(inspect_result.stdout)[0]
            is_running = container_info['State']['Running']
            
            if is_running:
                return {"message": f"Container {container_name} is already running", "success": True}
            else:
                # 종료된 컨테이너 - 제거 후 새로 실행
                subprocess.run(["docker", "rm", container_name], capture_output=True)
        
        # 새 컨테이너 실행
        if docker_image:
            run_result = subprocess.run(
                ["docker", "run", "--name", container_name, "-d", docker_image], 
                capture_output=True, text=True
            )
        else:
            return {"error": "No docker image specified for this job", "success": False}
        
        if run_result.returncode != 0:
            return {"error": f"Failed to start: {run_result.stderr.strip()}", "success": False}
        
        # 기존 RUNNING 상태가 있다면 CANCELLED로 변경 (중복 방지)
        kst_now = datetime.now(KST)
        db.execute(
            text("""
                UPDATE JobRuns 
                SET status = 'CANCELLED', finished_at = :finished_at
                WHERE job_id = :job_id AND status = 'RUNNING'
            """),
            {"job_id": job_id, "finished_at": kst_now}
        )
        
        # JobRuns에 새 세션 시작 기록 (RUNNING 상태)
        run_id = str(uuid.uuid4())
        db.execute(
            text("""
                INSERT INTO JobRuns (run_id, job_id, run_type_id, triggered_by_user_id, status, started_at)
                VALUES (:run_id, :job_id, 
                        (SELECT run_type_id FROM RunTypes WHERE name = 'MANUAL' LIMIT 1),
                        (SELECT user_id FROM Users WHERE username = 'admin' LIMIT 1),
                        'RUNNING', :started_at)
            """),
            {"run_id": run_id, "job_id": job_id, "started_at": kst_now}
        )
        
        db.commit()
        
        return {"message": f"Container {container_name} started", "success": True}
        
    except Exception as e:
        db.rollback()
        return {"error": f"Error: {str(e)}", "success": False}

def save_container_logs_to_audit(container_name: str, job_id: str, db: Session):
    """컨테이너 로그를 audit logs에 저장"""
    try:
        import subprocess
        
        # 컨테이너 로그 가져오기 (tail 500)
        logs_cmd = ["docker", "logs", "--tail=500", container_name]
        result = subprocess.run(logs_cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            # Audit 로그에 컨테이너 로그 저장
            db.execute(
                text("""
                    INSERT INTO AuditLogs (user_id, action_type, target_type, target_id, after_value)
                    VALUES ((SELECT user_id FROM Users WHERE username = 'system' LIMIT 1),
                            'CONTAINER_LOGS', 'job', :job_id, 
                            JSON_OBJECT('container_name', :container_name, 'logs', :logs))
                """),
                {
                    "job_id": job_id, 
                    "container_name": container_name,
                    "logs": result.stdout[:10000]  # 로그 크기 제한 (10KB)
                }
            )
            print(f"Container logs saved to audit for {container_name}")
        
    except Exception as e:
        print(f"Failed to save container logs: {e}")

@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Job 및 관련 데이터 완전 삭제"""
    try:
        # Job 존재 확인
        job_result = db.execute(
            text("SELECT name FROM Jobs WHERE job_id = :job_id"),
            {"job_id": job_id}
        ).fetchone()
        
        if not job_result:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_name = job_result[0]
        
        # 1. 스케줄러로 생성된 컨테이너들 강제 종료 및 제거
        try:
            import subprocess
            # scheduled-{job_name}-* 패턴의 컨테이너들 찾기
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name=scheduled-{job_name}", "--format", "{{.Names}}"],
                capture_output=True, text=True
            )
            
            if result.stdout.strip():
                container_names = result.stdout.strip().split('\n')
                for container_name in container_names:
                    if container_name:
                        # 컨테이너 강제 종료 및 제거
                        subprocess.run(["docker", "stop", container_name], capture_output=True)
                        subprocess.run(["docker", "rm", container_name], capture_output=True)
                        print(f"🗑️ Removed scheduled container: {container_name}")
        except Exception as e:
            print(f"⚠️ Error cleaning up scheduled containers: {e}")
        
        # 2. 데이터베이스에서 관련 데이터 삭제 (기존 순서 유지)
        db.execute(text("DELETE FROM JobRunErrors WHERE run_id IN (SELECT run_id FROM JobRuns WHERE job_id = :job_id)"), {"job_id": job_id})
        db.execute(text("DELETE FROM JobRunLogs WHERE run_id IN (SELECT run_id FROM JobRuns WHERE job_id = :job_id)"), {"job_id": job_id})
        db.execute(text("DELETE FROM JobRuns WHERE job_id = :job_id"), {"job_id": job_id})
        db.execute(text("DELETE FROM JobSchedules WHERE job_id = :job_id"), {"job_id": job_id})
        
        # 3. Job 삭제
        result = db.execute(
            text("DELETE FROM Jobs WHERE job_id = :job_id"),
            {"job_id": job_id}
        )
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Job not found")
        
        db.commit()
        return {"message": f"Job '{job_name}' and all related data (including scheduled containers) deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@app.post("/api/containers/{job_id}/stop")
def stop_container(job_id: str, db: Session = Depends(get_db)):
    """컨테이너 정지"""
    try:
        import subprocess
        
        # job_id로 컨테이너 이름 조회
        result = db.execute(
            text("SELECT name FROM Jobs WHERE job_id = :job_id"),
            {"job_id": job_id}
        ).fetchone()
        
        if not result:
            return {"error": "Container not found", "success": False}
        
        container_name = result[0]
        
        stop_result = subprocess.run(
            ["docker", "stop", container_name], 
            capture_output=True, text=True
        )
        
        if stop_result.returncode != 0:
            return {"error": f"Failed to stop: {stop_result.stderr.strip()}", "success": False}
        
        # 컨테이너 로그를 audit logs에 저장 (tail 500)
        save_container_logs_to_audit(container_name, job_id, db)
        
        # 기존 RUNNING 세션을 SUCCESS로 완료 처리 (수동 정지)
        kst_now = datetime.now(KST)
        db.execute(
            text("""
                UPDATE JobRuns 
                SET status = 'SUCCESS', finished_at = :finished_at, exit_code = 0
                WHERE job_id = :job_id AND status = 'RUNNING'
                ORDER BY started_at DESC LIMIT 1
            """),
            {"job_id": job_id, "finished_at": kst_now}
        )
        
        db.commit()
        
        return {"message": f"Container {container_name} stopped", "success": True}
        
    except Exception as e:
        db.rollback()
        return {"error": f"Error: {str(e)}", "success": False}

@app.get("/api/runs/{run_id}/logs")
def get_job_run_logs(run_id: str, db: Session = Depends(get_db)):
    """특정 Job Run의 로그 조회"""
    result = db.execute(
        text("""
        SELECT log_id, run_id, log_text, created_at
        FROM JobRunLogs 
        WHERE run_id = :run_id 
        ORDER BY created_at DESC
        """),
        {"run_id": run_id}
    ).fetchall()
    
    return [
        {
            "log_id": row[0],
            "run_id": row[1], 
            "log_text": row[2],
            "created_at": row[3].isoformat() if row[3] else None
        }
        for row in result
    ]

@app.get("/api/runs")
def get_job_runs(limit: int = 50, db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            SELECT jr.run_id, j.name, jr.status, jr.started_at, 
                   jr.finished_at, jr.exit_code, u.username, a.hostname, rt.name as run_type
            FROM JobRuns jr
            JOIN Jobs j ON jr.job_id = j.job_id
            LEFT JOIN Users u ON jr.triggered_by_user_id = u.user_id
            LEFT JOIN Agents a ON jr.agent_id = a.agent_id
            LEFT JOIN RunTypes rt ON jr.run_type_id = rt.run_type_id
            LIMIT :limit
        """),
        {"limit": limit}
    ).fetchall()
    
    return [
        {
            "run_id": row[0],
            "job_name": row[1],
            "status": row[2],
            "started_at": row[3].isoformat() if row[3] else None,
            "finished_at": row[4].isoformat() if row[4] else None,
            "exit_code": row[5],
            "user": row[6] or "System",
            "hostname": row[7] or "Unknown",
            "run_type": row[8] or "UNKNOWN"
        }
        for row in result
    ]

class JobCompletion(BaseModel):
    status: str  # SUCCESS, FAILED, CANCELLED
    finished_at: str
    exit_code: Optional[int] = None
    result: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    logs: Optional[str] = None

@app.post("/api/schedules")
def create_schedule(schedule: JobScheduleCreate, db: Session = Depends(get_db)):
    """Job 스케줄 생성"""
    try:
        schedule_id = str(uuid.uuid4())
        
        db.execute(
            text("""
                INSERT INTO JobSchedules (schedule_id, job_id, cron_expression, is_active)
                VALUES (:schedule_id, :job_id, :cron_expression, :is_active)
            """),
            {
                "schedule_id": schedule_id,
                "job_id": schedule.job_id,
                "cron_expression": schedule.cron_expression,
                "is_active": schedule.is_active
            }
        )
        
        db.commit()
        return {"schedule_id": schedule_id, "message": "Schedule created"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/schedules")
def get_schedules(db: Session = Depends(get_db)):
    """스케줄 목록 조회"""
    result = db.execute(
        text("""
            SELECT s.schedule_id, s.cron_expression, s.is_active, s.created_at,
                   j.name as job_name, j.job_id
            FROM JobSchedules s
            JOIN Jobs j ON s.job_id = j.job_id
            ORDER BY s.created_at DESC
        """)
    ).fetchall()
    
    return [
        {
            "schedule_id": row[0],
            "cron_expression": row[1],
            "is_active": row[2],
            "created_at": row[3].isoformat() if row[3] else None,
            "job_name": row[4],
            "job_id": row[5]
        }
        for row in result
    ]

@app.post("/api/audit-logs")
def create_audit_log(audit: AuditLogCreate, db: Session = Depends(get_db)):
    """Audit 로그 생성"""
    try:
        # 사용자 확인/생성
        user_result = db.execute(
            text("SELECT user_id FROM Users WHERE username = :username"),
            {"username": audit.user}
        ).fetchone()
        
        if not user_result:
            user_id = str(uuid.uuid4())
            db.execute(
                text("""
                    INSERT INTO Users (user_id, username, email, role) 
                    VALUES (:user_id, :username, :email, 'developer')
                """),
                {
                    "user_id": user_id,
                    "username": audit.user,
                    "email": f"{audit.user}@auto-detected.local"
                }
            )
        else:
            user_id = user_result[0]
        
        # Audit 로그 생성
        db.execute(
            text("""
                INSERT INTO AuditLogs (user_id, action_type, target_type, target_id, after_value)
                VALUES (:user_id, :action_type, :target_type, :target_id, :after_value)
            """),
            {
                "user_id": user_id,
                "action_type": audit.action_type,
                "target_type": audit.target_type,
                "target_id": audit.target_id,
                "after_value": json.dumps(audit.details or {})
            }
        )
        
        db.commit()
        return {"message": "Audit log created"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audit-logs")
def get_audit_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Audit 로그 조회"""
    result = db.execute(
        text("""
            SELECT a.audit_id, u.username, a.action_type, a.target_type, 
                   a.target_id, a.after_value, a.created_at
            FROM AuditLogs a
            LEFT JOIN Users u ON a.user_id = u.user_id
            ORDER BY a.created_at DESC
            LIMIT :limit
        """),
        {"limit": limit}
    ).fetchall()
    
    return [
        {
            "audit_id": row[0],
            "username": row[1],
            "action_type": row[2],
            "target_type": row[3],
            "target_id": row[4],
            "details": json.loads(row[5]) if row[5] else {},
            "created_at": row[6].replace(tzinfo=pytz.UTC).astimezone(KST).isoformat() if row[6] else None,
            "is_failed": json.loads(row[5]).get("status") == "FAILED" if row[5] and json.loads(row[5]).get("status") else False,
            "error_type": json.loads(row[5]).get("error_type") if row[5] and json.loads(row[5]).get("error_type") else None
        }
        for row in result
    ]

@app.get("/api/container-logs/{container_id}")
def get_container_logs(container_id: str, tail: int = 100, since: str = None):
    try:
        import subprocess
        import json
        
        print(f"Fetching logs for container: {container_id}")
        
        # 컨테이너 존재 확인
        try:
            inspect_cmd = ["docker", "inspect", container_id]
            result = subprocess.run(inspect_cmd, capture_output=True, text=True, check=True)
            container_info = json.loads(result.stdout)[0]
            print(f"Container found: {container_info['Name']}")
        except subprocess.CalledProcessError as e:
            print(f"Container not found: {e.stderr}")
            raise HTTPException(status_code=404, detail="Container not found")
        
        # 로그 가져오기
        logs_cmd = ["docker", "logs", "--timestamps", f"--tail={tail}", container_id]
        if since:
            logs_cmd.extend(["--since", since])
            
        print(f"Running command: {' '.join(logs_cmd)}")
        result = subprocess.run(logs_cmd, capture_output=True, text=True, check=True)
        logs = result.stdout
        print(f"Got {len(logs)} characters of logs")
        
        log_lines = []
        for line in logs.strip().split('\n'):
            if line.strip():
                # 타임스탬프와 메시지 분리
                if 'T' in line and 'Z' in line:  # ISO timestamp format
                    parts = line.split(' ', 1)
                    if len(parts) >= 2:
                        timestamp = parts[0]
                        message = parts[1]
                    else:
                        timestamp = ''
                        message = line
                else:
                    timestamp = ''
                    message = line
                    
                log_lines.append({
                    'timestamp': timestamp,
                    'message': message
                })
        
        return {
            'container_id': container_id,
            'container_name': container_info['Name'].lstrip('/'),
            'logs': log_lines[-tail:] if tail else log_lines
        }
        
    except subprocess.CalledProcessError as e:
        print(f"Docker command failed: {e.stderr}")
        if "No such container" in e.stderr:
            raise HTTPException(status_code=404, detail="Container not found")
        raise HTTPException(status_code=500, detail=f"Docker command failed: {e.stderr}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/schedules/{schedule_id}/toggle")
def toggle_schedule(schedule_id: str, request: dict):
    try:
        with engine.connect() as db:
            # 기존 값 조회
            old_schedule = db.execute(
                text("SELECT is_active FROM JobSchedules WHERE schedule_id = :schedule_id"),
                {"schedule_id": schedule_id}
            ).fetchone()
            
            # 스케줄 업데이트
            db.execute(
                text("UPDATE JobSchedules SET is_active = :is_active WHERE schedule_id = :schedule_id"),
                {"is_active": request["is_active"], "schedule_id": schedule_id}
            )
            
            # Audit Log 기록
            user_result = db.execute(
                text("SELECT user_id FROM Users WHERE username = 'eunji' LIMIT 1")
            ).fetchone()
            
            if user_result and old_schedule:
                action_type = "ACTIVATE_SCHEDULE" if request["is_active"] else "DEACTIVATE_SCHEDULE"
                db.execute(
                    text("""
                        INSERT INTO AuditLogs (user_id, action_type, target_type, target_id, before_value, after_value)
                        VALUES (:user_id, :action_type, 'schedule', :target_id, :before_value, :after_value)
                    """),
                    {
                        "user_id": user_result[0],
                        "action_type": action_type,
                        "target_id": schedule_id,
                        "before_value": json.dumps({"is_active": old_schedule[0]}),
                        "after_value": json.dumps({"is_active": request["is_active"]})
                    }
                )
            
            db.commit()
            return {"message": "Schedule updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/schedules/{schedule_id}")
def delete_schedule(schedule_id: str):
    try:
        with engine.connect() as db:
            # 삭제 전 정보 조회
            old_schedule = db.execute(
                text("SELECT job_id, cron_expression, is_active FROM JobSchedules WHERE schedule_id = :schedule_id"),
                {"schedule_id": schedule_id}
            ).fetchone()
            
            # 스케줄 삭제
            db.execute(
                text("DELETE FROM JobSchedules WHERE schedule_id = :schedule_id"),
                {"schedule_id": schedule_id}
            )
            
            # Audit Log 기록
            user_result = db.execute(
                text("SELECT user_id FROM Users WHERE username = 'eunji' LIMIT 1")
            ).fetchone()
            
            if user_result and old_schedule:
                db.execute(
                    text("""
                        INSERT INTO AuditLogs (user_id, action_type, target_type, target_id, before_value)
                        VALUES (:user_id, 'DELETE_SCHEDULE', 'schedule', :target_id, :before_value)
                    """),
                    {
                        "user_id": user_result[0],
                        "target_id": schedule_id,
                        "before_value": json.dumps({
                            "job_id": old_schedule[0],
                            "cron_expression": old_schedule[1],
                            "is_active": old_schedule[2]
                        })
                    }
                )
            
            db.commit()
            return {"message": "Schedule deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/schedules")
def create_schedule(schedule: dict):
    try:
        with engine.connect() as db:
            schedule_id = str(uuid.uuid4())
            
            # 스케줄 생성
            db.execute(
                text("""
                    INSERT INTO JobSchedules (schedule_id, job_id, cron_expression, is_active)
                    VALUES (:schedule_id, :job_id, :cron_expression, TRUE)
                """),
                {
                    "schedule_id": schedule_id,
                    "job_id": schedule["job_id"],
                    "cron_expression": schedule["cron_expression"]
                }
            )
            
            # Audit Log 기록
            user_result = db.execute(
                text("SELECT user_id FROM Users WHERE username = 'eunji' LIMIT 1")
            ).fetchone()
            
            if user_result:
                db.execute(
                    text("""
                        INSERT INTO AuditLogs (user_id, action_type, target_type, target_id, after_value)
                        VALUES (:user_id, 'CREATE_SCHEDULE', 'schedule', :target_id, :after_value)
                    """),
                    {
                        "user_id": user_result[0],
                        "target_id": schedule_id,
                        "after_value": json.dumps({
                            "job_id": schedule["job_id"],
                            "cron_expression": schedule["cron_expression"]
                        })
                    }
                )
            
            db.commit()
            return {"message": "Schedule created successfully", "schedule_id": schedule_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs/{job_id}/run")
def run_job_manually(job_id: str, db: Session = Depends(get_db)):
    """Job 수동 실행"""
    try:
        # MANUAL run_type_id 조회
        manual_type = db.execute(
            text("SELECT run_type_id FROM RunTypes WHERE name = 'MANUAL'")
        ).fetchone()
        
        if not manual_type:
            raise HTTPException(status_code=500, detail="MANUAL run type not found")
        
        # 사용자 정보 조회
        user_result = db.execute(
            text("SELECT user_id FROM Users WHERE username = 'eunji' LIMIT 1")
        ).fetchone()
        
        # 기본 에이전트 조회 (로컬 실행용)
        agent_result = db.execute(
            text("SELECT agent_id FROM Agents WHERE name LIKE '%local%' OR name LIKE '%manual%' LIMIT 1")
        ).fetchone()
        
        run_id = str(uuid.uuid4())
        
        # JobRuns에 수동 실행 기록
        db.execute(
            text("""
                INSERT INTO JobRuns (run_id, job_id, run_type_id, triggered_by_user_id, agent_id, status, started_at)
                VALUES (:run_id, :job_id, :run_type_id, :user_id, :agent_id, 'RUNNING', CONVERT_TZ(NOW(), 'UTC', 'Asia/Seoul'))
            """),
            {
                "run_id": run_id,
                "job_id": job_id,
                "run_type_id": manual_type[0],
                "user_id": user_result[0] if user_result else None,
                "agent_id": agent_result[0] if agent_result else None
            }
        )
        
        db.commit()
        return {"message": "Job execution started", "run_id": run_id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

class JobRunError(BaseModel):
    run_id: str
    error_type: str
    message: str
    logs: Optional[str] = None

@app.post("/api/job-run-errors")
def create_job_run_error(error: JobRunError, db: Session = Depends(get_db)):
    """Job 실행 오류 기록"""
    try:
        # ErrorType 확인
        error_type_result = db.execute(
            text("SELECT error_type_id FROM ErrorTypes WHERE name = :error_type"),
            {"error_type": error.error_type}
        ).fetchone()
        
        if error_type_result:
            error_type_id = error_type_result[0]
        else:
            # 새로운 오류 유형 생성
            error_type_id = str(uuid.uuid4())
            db.execute(
                text("INSERT INTO ErrorTypes (error_type_id, name) VALUES (:id, :name)"),
                {"id": error_type_id, "name": error.error_type}
            )
        
        # JobRunError 생성
        db.execute(
            text("""
                INSERT INTO JobRunErrors (error_id, run_id, error_type_id, message, stacktrace)
                VALUES (:error_id, :run_id, :error_type_id, :message, :stacktrace)
            """),
            {
                "error_id": str(uuid.uuid4()),
                "run_id": error.run_id,
                "error_type_id": error_type_id,
                "message": error.message,
                "stacktrace": error.logs
            }
        )
        
        db.commit()
        return {"message": "Error recorded successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/test")
def test_auto_reload():
    return {"message": "Auto-reload is working!", "timestamp": "2025-12-12 19:15:30"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
@app.get("/api/users")
def get_users(db: Session = Depends(get_db)):
    """DB에 저장된 사용자 목록 조회"""
    try:
        result = db.execute(text("""
            SELECT user_id, username, email, created_at 
            FROM Users 
            ORDER BY created_at DESC
        """)).fetchall()
        
        users = []
        for row in result:
            users.append({
                'user_id': row[0],
                'username': row[1], 
                'email': row[2],
                'created_at': row[3].isoformat() if row[3] else None
            })
        
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")

@app.get("/api/system-users")
def get_system_users():
    """시스템 사용자 목록 조회"""
    try:
        import subprocess
        # macOS에서 사용자 목록 조회
        result = subprocess.run(['dscl', '.', 'list', '/Users'], capture_output=True, text=True)
        users = []
        
        for username in result.stdout.strip().split('\n'):
            if username and not username.startswith('_') and username not in ['daemon', 'nobody', 'root']:
                try:
                    uid_result = subprocess.run(['id', '-u', username], capture_output=True, text=True)
                    if uid_result.returncode == 0:
                        uid = int(uid_result.stdout.strip())
                        if uid >= 500:  # macOS 일반 사용자
                            users.append({
                                'username': username,
                                'uid': uid,
                                'gid': 0,
                                'home_dir': f'/Users/{username}',
                                'shell': '/bin/bash'
                            })
                except:
                    continue
        
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system users: {str(e)}")

@app.post("/api/users/sync")
def sync_users_from_system(db: Session = Depends(get_db)):
    """시스템 사용자를 DB에 동기화"""
    try:
        # 시스템 사용자 조회
        system_users = get_system_users()
        synced_count = 0
        
        for user in system_users:
            # DB에 이미 존재하는지 확인
            existing = db.execute(
                text("SELECT user_id FROM Users WHERE username = :username"),
                {"username": user['username']}
            ).fetchone()
            
            if not existing:
                # 새 사용자 추가
                user_id = str(uuid.uuid4())
                db.execute(text("""
                    INSERT INTO Users (user_id, username, email, role, created_at)
                    VALUES (:user_id, :username, :email, 'developer', NOW())
                """), {
                    "user_id": user_id,
                    "username": user['username'],
                    "email": f"{user['username']}@localhost"
                })
                synced_count += 1
        
        db.commit()
        return {"message": f"Synced {synced_count} new users from system", "total_system_users": len(system_users)}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
