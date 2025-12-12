#!/usr/bin/env python3
"""
호스트 레벨 Job 추적 에이전트
- 실행 중인 모든 컨테이너 자동 감지
- Docker 이벤트 실시간 모니터링
- 설정 없이 자동 추적
"""

import docker
import psutil
import time
import threading
import requests
import json
import os
from datetime import datetime
from typing import Dict, Set
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HostJobAgent:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url.rstrip('/')
        self.client = None
        self.tracked_containers: Dict[str, dict] = {}
        self.running = False
        
        try:
            self.client = docker.from_env()
            logger.info("Docker client connected")
        except Exception as e:
            logger.error(f"Docker not available: {e}")
    
    def is_job_container(self, container) -> bool:
        """모든 컨테이너를 Job으로 인식"""
        return True  # 모든 컨테이너 추적
    
    def extract_job_info(self, container) -> dict:
        """컨테이너에서 Job 정보 추출"""
        labels = container.labels or {}
        
        # 실제 호스트 사용자 정보 수집
        import getpass
        import pwd
        
        try:
            # 현재 로그인 사용자
            current_user = getpass.getuser()
            
            # 추가 사용자 정보
            user_info = pwd.getpwnam(current_user)
            real_name = user_info.pw_gecos.split(',')[0] if user_info.pw_gecos else current_user
            
        except Exception as e:
            logger.warning(f"Failed to get user info: {e}")
            current_user = "unknown"
            real_name = "unknown"
        
        return {
            "name": labels.get('job.name', container.name),
            "type": labels.get('job.type', 'CONTAINER'),
            "description": labels.get('job.description', f"Auto-detected container job: {container.name}"),
            "container_id": container.id,
            "container_name": container.name,
            "image": container.image.tags[0] if container.image and container.image.tags else 'unknown',
            "user": labels.get('job.user', current_user),  # 호스트 사용자
            "user_real_name": real_name,  # 실제 이름
            "hostname": container.name,
            "started_at": datetime.now().isoformat(),
            "auto_detected": True,
            "host_user": current_user  # 호스트 사용자 명시적 기록
        }
    
    def register_job_start(self, job_info: dict) -> str:
        """중앙 API에 Job 시작 등록"""
        try:
            response = requests.post(
                f"{self.api_url}/api/jobs/auto-register",
                json=job_info,
                timeout=5
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Registered job: {job_info['name']} -> {result.get('run_id')}")
            return result.get('run_id')
        except Exception as e:
            logger.warning(f"Failed to register job: {e}")
            return None
    
    def register_job_completion(self, run_id: str, container):
        """Job 완료 등록 - 상세 오류 분석 포함"""
        if not run_id:
            return
            
        try:
            # 컨테이너 상태 확인
            container.reload()
            exit_code = container.attrs['State']['ExitCode']
            status = "SUCCESS" if exit_code == 0 else "FAILED"
            
            # 로그 수집
            try:
                logs = container.logs(tail=500).decode('utf-8', errors='ignore')
            except:
                logs = "Failed to retrieve logs"
            
            # 오류 분석
            error_info = None
            if status == "FAILED":
                error_info = self._analyze_error(exit_code, logs)
            
            completion_data = {
                "status": status,
                "exit_code": exit_code,
                "finished_at": datetime.now().isoformat(),
                "logs": logs
            }
            
            if error_info:
                completion_data["error"] = error_info["message"]
                completion_data["error_type"] = error_info["type"]
            
            response = requests.put(
                f"{self.api_url}/api/runs/{run_id}/complete",
                json=completion_data,
                timeout=5
            )
            response.raise_for_status()
            logger.info(f"Completed job: {run_id} -> {status}")
            
        except Exception as e:
            logger.warning(f"Failed to register completion: {e}")
    
    def _analyze_error(self, exit_code: int, logs: str) -> dict:
        """오류 상세 분석"""
        error_type = "UNKNOWN"
        message = f"Container exited with code {exit_code}"
        
        # Exit code 기반 분류
        if exit_code == 137:
            error_type = "KILLED_OOM"
            message = "Container killed (likely out of memory)"
        elif exit_code == 143:
            error_type = "TERMINATED"
            message = "Container terminated by signal"
        elif exit_code == 1:
            error_type = "GENERAL_ERROR"
        
        # 로그에서 오류 패턴 찾기
        import re
        log_lines = logs.split('\n')[-20:]  # 마지막 20줄
        
        for line in log_lines:
            if re.search(r'(?i)error:', line):
                error_type = "APPLICATION_ERROR"
                message = line.strip()
                break
            elif re.search(r'(?i)exception:', line):
                error_type = "EXCEPTION"
                message = line.strip()
                break
            elif re.search(r'(?i)timeout:', line):
                error_type = "TIMEOUT"
                message = line.strip()
                break
        
        return {
            "type": error_type,
            "message": message,
            "exit_code": exit_code
        }
    
    def scan_existing_containers(self):
        """현재 실행 중인 컨테이너 스캔"""
        if not self.client:
            return
            
        logger.info("Scanning existing containers...")
        try:
            containers = self.client.containers.list()
            for container in containers:
                if self.is_job_container(container):
                    if container.id not in self.tracked_containers:
                        self.start_tracking_container(container)
                        
        except Exception as e:
            logger.error(f"Error scanning containers: {e}")
    
    def start_tracking_container(self, container):
        """컨테이너 추적 시작"""
        try:
            job_info = self.extract_job_info(container)
            run_id = self.register_job_start(job_info)
            
            self.tracked_containers[container.id] = {
                'run_id': run_id,
                'container': container,
                'start_time': time.time(),
                'user': job_info['user']  # 사용자 정보 저장
            }
            
            logger.info(f"Started tracking: {container.name} ({container.id[:12]}) by user: {job_info['user']}")
            
            # Audit 로그 생성 (사용자가 컨테이너 실행한 경우)
            self._create_audit_log(job_info, container)
            
            # 별도 스레드에서 완료 대기
            threading.Thread(
                target=self.wait_for_completion,
                args=(container.id,),
                daemon=True
            ).start()
            
        except Exception as e:
            logger.error(f"Error starting tracking: {e}")
    
    def _create_audit_log(self, job_info: dict, container):
        """Audit 로그 생성"""
        try:
            # 컨테이너가 최근에 생성된 경우만 사용자 액션으로 간주
            created_time = container.attrs['Created']
            created_dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
            now = datetime.now(created_dt.tzinfo)
            
            # 5분 이내에 생성된 컨테이너만 사용자 액션으로 기록
            if (now - created_dt).total_seconds() < 300:
                audit_data = {
                    "user": job_info['user'],
                    "action_type": "CONTAINER_START",
                    "target_type": "container",
                    "target_id": container.id,
                    "details": {
                        "container_name": container.name,
                        "image": job_info.get('image', 'unknown'),
                        "hostname": job_info['hostname'],
                        "auto_detected": True
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                # Audit API 호출 (별도 엔드포인트 필요)
                try:
                    response = requests.post(
                        f"{self.api_url}/api/audit-logs",
                        json=audit_data,
                        timeout=5
                    )
                    if response.status_code == 200:
                        logger.info(f"Audit log created for user: {job_info['user']}")
                except Exception as e:
                    logger.warning(f"Failed to create audit log: {e}")
                    
        except Exception as e:
            logger.warning(f"Error creating audit log: {e}")
    
    def wait_for_completion(self, container_id: str):
        """컨테이너 완료 대기"""
        try:
            if container_id not in self.tracked_containers:
                return
                
            container_info = self.tracked_containers[container_id]
            container = container_info['container']
            run_id = container_info['run_id']
            
            # 컨테이너 완료까지 대기
            result = container.wait()
            
            # 완료 처리
            self.register_job_completion(run_id, container)
            
            # 추적 목록에서 제거
            if container_id in self.tracked_containers:
                del self.tracked_containers[container_id]
                
        except Exception as e:
            logger.error(f"Error waiting for completion: {e}")
    
    def monitor_docker_events(self):
        """Docker 이벤트 실시간 모니터링"""
        if not self.client:
            return
            
        logger.info("Starting Docker event monitoring...")
        try:
            for event in self.client.events(decode=True):
                if not self.running:
                    break
                    
                if event['Type'] == 'container':
                    if event['Action'] == 'start':
                        # 새 컨테이너 시작
                        container_id = event['id']
                        try:
                            container = self.client.containers.get(container_id)
                            if self.is_job_container(container):
                                self.start_tracking_container(container)
                        except Exception as e:
                            logger.error(f"Error handling start event: {e}")
                            
                    elif event['Action'] in ['die', 'kill']:
                        # 컨테이너 종료
                        container_id = event['id']
                        if container_id in self.tracked_containers:
                            logger.info(f"Container stopped: {container_id[:12]}")
                            
        except Exception as e:
            logger.error(f"Error monitoring events: {e}")
    
    def start(self):
        """에이전트 시작"""
        logger.info("Starting Host Job Agent...")
        self.running = True
        
        # 기존 컨테이너 스캔
        self.scan_existing_containers()
        
        # Docker 이벤트 모니터링 시작
        if self.client:
            event_thread = threading.Thread(target=self.monitor_docker_events, daemon=True)
            event_thread.start()
        
        # 주기적 상태 체크
        try:
            while self.running:
                logger.info(f"Tracking {len(self.tracked_containers)} containers")
                time.sleep(30)  # 30초마다 상태 출력
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.running = False

def main():
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Host Job Agent')
    parser.add_argument('--api-url', default='http://localhost:8000', 
                       help='Job Management API URL')
    parser.add_argument('--config', help='Config file path')
    args = parser.parse_args()
    
    api_url = args.api_url
    
    # 설정 파일이 있으면 읽기
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config) as f:
                config = json.load(f)
                api_url = config.get('api_url', api_url)
        except Exception as e:
            logger.warning(f"Failed to read config: {e}")
    
    agent = HostJobAgent(api_url)
    agent.start()

if __name__ == "__main__":
    main()
