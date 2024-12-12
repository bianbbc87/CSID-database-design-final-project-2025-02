#!/usr/bin/env python3
"""
Container Monitor - 로컬에서 실행되는 모든 컨테이너를 감지하고 기록
"""

import time
import subprocess
import requests
import json
import os
from datetime import datetime
import pytz

KST = pytz.timezone('Asia/Seoul')
API_BASE = os.getenv("JOB_TRACKER_API_URL", "http://localhost:8000")

# 이미 처리된 컨테이너 추적
processed_containers = set()

def get_container_info():
    """현재 실행 중인 모든 컨테이너 정보 조회"""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}\t{{.ID}}\t{{.Image}}\t{{.CreatedAt}}"],
            capture_output=True, text=True, check=True
        )
        
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 5:
                    name, status, container_id, image, created_at = parts
                    
                    # 시스템 컨테이너 제외
                    if name.startswith(('job_management_', 'job_container_monitor', 'job_scheduler')):
                        continue
                        
                    containers.append({
                        'name': name,
                        'status': status,
                        'container_id': container_id,
                        'image': image,
                        'created_at': created_at
                    })
        return containers
    except Exception as e:
        print(f"Error getting container info: {e}")
        return []

def analyze_error_type(logs, exit_code):
    """로그 내용과 exit code를 분석해서 오류 유형 판단"""
    if exit_code == 0:
        return None  # 성공한 경우 오류 없음
    
    logs_lower = logs.lower() if logs else ""
    
    # 권한 오류 패턴
    permission_patterns = [
        'permission denied', 'access denied', 'forbidden', 
        'unauthorized', 'not allowed', 'sudo required'
    ]
    
    # 리소스 오류 패턴  
    resource_patterns = [
        'out of memory', 'memory limit', 'disk space', 'no space left',
        'resource temporarily unavailable', 'cannot allocate memory',
        'killed', 'oomkilled'
    ]
    
    # 타임아웃 패턴
    timeout_patterns = [
        'timeout', 'timed out', 'connection timeout', 'read timeout',
        'deadline exceeded', 'context deadline exceeded'
    ]
    
    # 스크립트 오류 패턴 (일반적인 실행 오류)
    script_patterns = [
        'syntax error', 'import error', 'module not found', 'command not found',
        'file not found', 'no such file', 'traceback', 'exception',
        'error:', 'failed:', 'cannot'
    ]
    
    # 패턴 매칭으로 오류 유형 판단
    for pattern in permission_patterns:
        if pattern in logs_lower:
            return 'PERMISSION_ERROR'
    
    for pattern in resource_patterns:
        if pattern in logs_lower:
            return 'RESOURCE_ERROR'
            
    for pattern in timeout_patterns:
        if pattern in logs_lower:
            return 'TIMEOUT'
    
    for pattern in script_patterns:
        if pattern in logs_lower:
            return 'SCRIPT_ERROR'
    
    # 특정 exit code 기반 판단
    if exit_code == 125:  # Docker container error
        return 'RESOURCE_ERROR'
    elif exit_code == 126:  # Permission/execution error
        return 'PERMISSION_ERROR'
    elif exit_code == 127:  # Command not found
        return 'SCRIPT_ERROR'
    elif exit_code == 137:  # SIGKILL (OOM)
        return 'RESOURCE_ERROR'
    elif exit_code == 143:  # SIGTERM (timeout)
        return 'TIMEOUT'
    elif exit_code == 255:  # Docker daemon error
        return 'RESOURCE_ERROR'
    elif exit_code > 128:  # Signal-based termination
        return 'RESOURCE_ERROR'
    
    # 기본값: 스크립트 오류
    return 'SCRIPT_ERROR'

def register_container_execution(container):
    """컨테이너 실행을 시스템에 등록"""
    try:
        # 컨테이너가 종료된 경우만 기록 (완료된 실행)
        if not container['status'].startswith('Exited'):
            return
            
        print(f"🔍 Processing container: {container['name']} - {container['status']}")
        
        # 이미 등록된 컨테이너인지 확인 (컨테이너 ID 기준)
        check_response = requests.get(f"{API_BASE}/api/runs", timeout=10)
        if check_response.status_code == 200:
            existing_runs = check_response.json()
            for run in existing_runs:
                # 컨테이너 ID로 중복 체크 (더 정확함)
                if (run.get('job_name') == container['name'] and 
                    run.get('container_id') == container['container_id']):
                    return
            
        # 컨테이너 실행 사용자 감지 (현재 로그인한 사용자)
        container_user = "system"  # 기본값
        try:
            # 현재 시스템 사용자 확인
            import os
            import getpass
            
            # 1. 환경변수에서 사용자 확인
            container_user = os.getenv('USER') or os.getenv('USERNAME') or getpass.getuser()
            
            # 2. Docker 컨테이너가 실행된 터미널의 사용자 확인
            if container_user in ['root', 'system']:
                try:
                    # who 명령어로 현재 로그인한 사용자 확인
                    who_result = subprocess.run(['who', 'am', 'i'], capture_output=True, text=True)
                    if who_result.returncode == 0 and who_result.stdout.strip():
                        container_user = who_result.stdout.split()[0]
                except:
                    pass
                    
        except Exception as e:
            print(f"⚠️ Could not detect container user: {e}")
        
        print(f"👤 Detected container user: {container_user}")
        
        # Exit code 추출
        exit_code = 0
        if 'Exited (' in container['status']:
            try:
                exit_code = int(container['status'].split('Exited (')[1].split(')')[0])
            except:
                exit_code = 0
        
        # 컨테이너 로그 가져오기
        log_result = subprocess.run(
            ["docker", "logs", "--tail=500", container['name']],
            capture_output=True, text=True
        )
        
        # Job 자동 등록 데이터
        job_data = {
            "name": container['name'],
            "type": "CONTAINER",
            "description": f"Auto-detected container: {container['image']}",
            "image": container['image'],
            "user": container_user,  # 감지된 사용자 사용
            "hostname": "docker-host",
            "started_at": datetime.now(KST).isoformat(),
            "container_id": container['container_id'],
            "container_name": container['name']
        }
        
        print(f"📤 Registering to API: {API_BASE}/api/jobs/auto-register")
        
        # 시스템에 Job 등록
        response = requests.post(f"{API_BASE}/api/jobs/auto-register", json=job_data, timeout=10)
        print(f"📥 Registration response: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            run_id = result.get('run_id')
            print(f"✅ Got run_id: {run_id}")
            
            if run_id:
                # 실행 완료 처리
                completion_data = {
                    "status": "SUCCESS" if exit_code == 0 else "FAILED",
                    "finished_at": datetime.now(KST).isoformat(),
                    "exit_code": exit_code,
                    "result": log_result.stdout[:5000] if log_result.stdout else "No output"
                }
                
                complete_response = requests.put(f"{API_BASE}/api/runs/{run_id}/complete", json=completion_data, timeout=10)
                print(f"✅ Completion response: {complete_response.status_code}")
                
                # 컨테이너 로그를 audit logs에 저장
                if log_result.stdout:
                    # 오류 유형 분석
                    error_type = analyze_error_type(log_result.stdout, exit_code)
                    
                    audit_data = {
                        "user": "system",
                        "action_type": "CONTAINER_LOGS",
                        "target_type": "job",
                        "target_id": run_id,
                        "details": {
                            "container_name": container['name'],
                            "logs": log_result.stdout[:10000],  # 10KB 제한
                            "exit_code": exit_code,
                            "status": "SUCCESS" if exit_code == 0 else "FAILED",
                            "error_type": error_type  # 오류 유형 추가
                        }
                    }
                    
                    audit_response = requests.post(f"{API_BASE}/api/audit-logs", json=audit_data, timeout=10)
                    print(f"📋 Audit log response: {audit_response.status_code}")
                    
                    # 실패한 경우 JobRunErrors 테이블에도 기록
                    if exit_code != 0 and error_type:
                        error_data = {
                            "run_id": run_id,
                            "error_type": error_type,
                            "message": f"Container failed with exit code {exit_code}",
                            "logs": log_result.stdout[:5000]  # 5KB 제한
                        }
                        
                        error_response = requests.post(f"{API_BASE}/api/job-run-errors", json=error_data, timeout=10)
                        print(f"🚨 Error log response: {error_response.status_code} (Type: {error_type})")
                
                print(f"✅ Registered container execution: {container['name']} (exit: {exit_code})")
        else:
            print(f"❌ Registration failed: {response.text}")
        
    except Exception as e:
        import traceback
        print(f"❌ Error registering container {container['name']}: {e}")
        print(f"🔍 Container data: {container}")
        print(f"📋 Traceback: {traceback.format_exc()}")

def main():
    """메인 모니터링 루프"""
    print("🔍 Container Monitor started - watching for completed containers")
    print(f"🔗 API Base: {API_BASE}")
    processed_containers = set()
    
    while True:
        try:
            containers = get_container_info()
            
            # 모든 종료된 컨테이너 처리
            for container in containers:
                if container['status'].startswith('Exited'):
                    container_key = f"{container['name']}-{container['status']}"
                    if container_key not in processed_containers:
                        register_container_execution(container)
                        processed_containers.add(container_key)
            
            # RUNNING 상태인 작업들이 실제로는 종료되었는지 확인
            try:
                response = requests.get(f"{API_BASE}/api/runs", timeout=5)
                if response.status_code == 200:
                    runs = response.json()
                    running_runs = [run for run in runs if run.get('status') == 'RUNNING']
                    print(f"🔍 Found {len(running_runs)} RUNNING jobs to check")
                    
                    for run in running_runs:
                        container_name = run.get('job_name')
                        run_id = run.get('run_id')
                        print(f"🔍 Checking container: {container_name} (run_id: {run_id})")
                        
                        # Docker에서 실제 상태 확인
                        result = subprocess.run(
                            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
                            capture_output=True, text=True
                        )
                        
                        docker_status = result.stdout.strip()
                        print(f"🐳 Docker status for {container_name}: {docker_status}")
                        
                        if docker_status.startswith('Exited'):
                            print(f"🔄 Updating completed job: {container_name} (run_id: {run_id})")
                            # 완료 처리
                            exit_code = 0
                            if 'Exited (' in docker_status:
                                try:
                                    exit_code = int(docker_status.split('Exited (')[1].split(')')[0])
                                except:
                                    exit_code = 1
                            
                            # 로그 가져오기
                            log_result = subprocess.run(["docker", "logs", container_name], capture_output=True, text=True)
                            
                            # 완료 API 호출
                            complete_data = {
                                "status": "SUCCESS" if exit_code == 0 else "FAILED",
                                "finished_at": datetime.now(KST).isoformat(),
                                "exit_code": exit_code,
                                "result": log_result.stdout[:5000] if log_result.stdout else "No output"
                            }
                            
                            complete_response = requests.put(f"{API_BASE}/api/runs/{run_id}/complete", json=complete_data, timeout=10)
                            print(f"📝 Complete response: {complete_response.status_code}")
                            if complete_response.status_code != 200:
                                print(f"❌ Complete error: {complete_response.text}")
                        else:
                            print(f"⏳ Container {container_name} still running: {docker_status}")
            except Exception as e:
                print(f"❌ Error checking running jobs: {e}")
            
            # 5초마다 체크
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n🛑 Container Monitor stopped")
            break
        except Exception as e:
            print(f"❌ Monitor error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
