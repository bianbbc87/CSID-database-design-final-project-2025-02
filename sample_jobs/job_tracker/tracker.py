import functools
import os
import getpass
import socket
import uuid
import json
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
import requests
import threading
import time

class JobTracker:
    def __init__(self, api_url: str = "http://localhost:8000", api_token: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_token = api_token or os.environ.get('JOB_TRACKER_TOKEN')
        self.session = requests.Session()
        if self.api_token:
            self.session.headers.update({'Authorization': f'Bearer {self.api_token}'})
    
    def get_execution_context(self) -> Dict[str, Any]:
        """현재 실행 컨텍스트 정보 수집"""
        return {
            "user": getpass.getuser(),
            "hostname": socket.gethostname(),
            "container_id": os.environ.get('HOSTNAME'),  # Docker container
            "pid": os.getpid(),
            "cwd": os.getcwd(),
            "environment": {
                "CONTAINER_NAME": os.environ.get('CONTAINER_NAME'),
                "JOB_ID": os.environ.get('JOB_ID'),
                "USER": os.environ.get('USER'),
                "SUDO_USER": os.environ.get('SUDO_USER')  # sudo로 실행된 경우 원본 사용자
            }
        }
    
    def register_job_start(self, job_info: Dict[str, Any]) -> str:
        """Job 실행 시작을 중앙 DB에 등록"""
        try:
            response = self.session.post(
                f"{self.api_url}/api/jobs/auto-register",
                json=job_info,
                timeout=5
            )
            response.raise_for_status()
            return response.json().get("run_id")
        except Exception as e:
            print(f"Warning: Failed to register job start: {e}")
            return str(uuid.uuid4())  # 오프라인 모드용 임시 ID
    
    def register_job_completion(self, run_id: str, status: str, 
                             result: Any = None, error: str = None, 
                             logs: str = None):
        """Job 완료를 중앙 DB에 기록"""
        try:
            completion_data = {
                "status": status,
                "finished_at": datetime.now().isoformat(),
                "exit_code": 0 if status == "SUCCESS" else 1
            }
            
            if result is not None:
                completion_data["result"] = str(result)
            if error:
                completion_data["error"] = error
            if logs:
                completion_data["logs"] = logs
            
            response = self.session.put(
                f"{self.api_url}/api/runs/{run_id}/complete",
                json=completion_data,
                timeout=5
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Warning: Failed to register job completion: {e}")

# 전역 tracker 인스턴스
_tracker = JobTracker()

def track_job(job_type: str = "GENERAL", 
              description: str = None,
              timeout: int = None,
              capture_output: bool = True):
    """
    Job 실행을 자동으로 추적하는 데코레이터
    
    Args:
        job_type: Job 유형 (ETL, BACKUP, CLEANUP 등)
        description: Job 설명
        timeout: 타임아웃 (초)
        capture_output: 출력 캡처 여부
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 실행 컨텍스트 수집
            context = _tracker.get_execution_context()
            
            # Job 정보 구성
            job_info = {
                "name": func.__name__,
                "type": job_type,
                "description": description or f"Auto-tracked job: {func.__name__}",
                "script_path": func.__code__.co_filename,
                "function_name": func.__name__,
                "started_at": datetime.now().isoformat(),
                **context
            }
            
            # 출력 캡처 설정
            captured_output = []
            original_print = None
            
            if capture_output:
                original_print = print
                def capture_print(*args, **kwargs):
                    captured_output.append(' '.join(str(arg) for arg in args))
                    original_print(*args, **kwargs)
                
                # print 함수 오버라이드
                import builtins
                builtins.print = capture_print
            
            # 중앙 DB에 실행 시작 등록
            run_id = _tracker.register_job_start(job_info)
            
            start_time = time.time()
            
            try:
                # 타임아웃 설정
                if timeout:
                    def timeout_handler():
                        time.sleep(timeout)
                        raise TimeoutError(f"Job {func.__name__} timed out after {timeout} seconds")
                    
                    timeout_thread = threading.Thread(target=timeout_handler)
                    timeout_thread.daemon = True
                    timeout_thread.start()
                
                # 원본 함수 실행
                print(f"[JobTracker] Starting job: {func.__name__} (run_id: {run_id})")
                result = func(*args, **kwargs)
                
                # 성공 처리
                execution_time = time.time() - start_time
                logs = '\n'.join(captured_output) if capture_output else None
                
                print(f"[JobTracker] Job completed successfully in {execution_time:.2f}s")
                
                _tracker.register_job_completion(
                    run_id, "SUCCESS", result=result, logs=logs
                )
                
                return result
                
            except Exception as e:
                # 실패 처리
                execution_time = time.time() - start_time
                error_msg = str(e)
                stack_trace = traceback.format_exc()
                logs = '\n'.join(captured_output) if capture_output else None
                
                print(f"[JobTracker] Job failed after {execution_time:.2f}s: {error_msg}")
                
                _tracker.register_job_completion(
                    run_id, "FAILED", 
                    error=f"{error_msg}\n\nStacktrace:\n{stack_trace}",
                    logs=logs
                )
                
                raise
            
            finally:
                # print 함수 복원
                if capture_output and original_print:
                    import builtins
                    builtins.print = original_print
        
        return wrapper
    return decorator

def set_tracker_config(api_url: str, api_token: str = None):
    """Tracker 설정 변경"""
    global _tracker
    _tracker = JobTracker(api_url, api_token)

def manual_job_start(job_name: str, job_type: str = "MANUAL", **kwargs) -> str:
    """수동으로 Job 시작 기록"""
    context = _tracker.get_execution_context()
    job_info = {
        "name": job_name,
        "type": job_type,
        "started_at": datetime.now().isoformat(),
        **context,
        **kwargs
    }
    return _tracker.register_job_start(job_info)

def manual_job_complete(run_id: str, status: str = "SUCCESS", **kwargs):
    """수동으로 Job 완료 기록"""
    _tracker.register_job_completion(run_id, status, **kwargs)
