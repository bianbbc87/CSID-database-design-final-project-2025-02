import docker
import threading
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
from .tracker import JobTracker

class ContainerJobMonitor:
    def __init__(self, tracker: JobTracker, poll_interval: int = 5):
        self.tracker = tracker
        self.poll_interval = poll_interval
        self.client = None
        self.monitoring = False
        self.tracked_containers = {}  # container_id -> run_id
        
        try:
            self.client = docker.from_env()
        except Exception as e:
            print(f"Warning: Docker not available: {e}")
    
    def start_monitoring(self):
        """컨테이너 모니터링 시작"""
        if not self.client:
            print("Docker client not available, skipping container monitoring")
            return
        
        self.monitoring = True
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # 주기적 상태 체크 스레드 시작
        status_thread = threading.Thread(target=self._periodic_status_check)
        status_thread.daemon = True
        status_thread.start()
        
        print("Container job monitoring started")
    
    def _periodic_status_check(self):
        """주기적으로 추적 중인 컨테이너 상태 체크"""
        while self.monitoring:
            try:
                time.sleep(30)  # 30초마다 체크
                
                for container_id in list(self.tracked_containers.keys()):
                    try:
                        container = self.client.containers.get(container_id)
                        
                        # 컨테이너가 종료되었는지 확인
                        if container.status in ['exited', 'dead']:
                            container_info = self.tracked_containers.get(container_id)
                            if container_info:
                                # 종료 처리
                                exit_code = container.attrs.get('State', {}).get('ExitCode', 1)
                                status = "SUCCESS" if exit_code == 0 else "FAILED"
                                
                                # 로그 수집
                                try:
                                    logs = container.logs().decode('utf-8', errors='ignore')
                                except Exception:
                                    logs = "Failed to retrieve container logs"
                                
                                error_msg = None
                                if exit_code != 0:
                                    error_msg = f"Container exited with code {exit_code}"
                                
                                self.tracker.register_job_completion(
                                    container_info['run_id'], status,
                                    error=error_msg,
                                    logs=logs
                                )
                                
                                print(f"Periodic check: Container {container.name} completed with status {status}")
                                del self.tracked_containers[container_id]
                                
                    except docker.errors.NotFound:
                        # 컨테이너가 삭제됨
                        container_info = self.tracked_containers.get(container_id)
                        if container_info:
                            self.tracker.register_job_completion(
                                container_info['run_id'], "FAILED",
                                error="Container was removed"
                            )
                            print(f"Periodic check: Container {container_id} was removed")
                            del self.tracked_containers[container_id]
                    except Exception as e:
                        print(f"Error checking container {container_id}: {e}")
                        
            except Exception as e:
                print(f"Error in periodic status check: {e}")
                time.sleep(5)
    
    def stop_monitoring(self):
        """컨테이너 모니터링 중지"""
        self.monitoring = False
    
    def _monitor_loop(self):
        """모니터링 메인 루프"""
        while self.monitoring:
            try:
                self._scan_containers()
                time.sleep(self.poll_interval)
            except Exception as e:
                print(f"Error in container monitoring: {e}")
                time.sleep(self.poll_interval)
    
    def _scan_containers(self):
        """실행 중인 컨테이너 스캔"""
        try:
            # 현재 실행 중인 컨테이너 목록
            current_containers = {c.id: c for c in self.client.containers.list()}
            
            # 새로 시작된 Job 컨테이너 감지
            for container_id, container in current_containers.items():
                if (container_id not in self.tracked_containers and 
                    self._is_job_container(container)):
                    self._start_tracking_container(container)
            
            # 종료된 컨테이너 처리
            finished_containers = set(self.tracked_containers.keys()) - set(current_containers.keys())
            for container_id in finished_containers:
                self._finish_tracking_container(container_id)
                
        except Exception as e:
            print(f"Error scanning containers: {e}")
    
    def _is_job_container(self, container) -> bool:
        """컨테이너가 Job인지 판단"""
        labels = container.labels or {}
        
        # 명시적 Job 라벨
        if any(key.startswith('job.') for key in labels.keys()):
            return True
        
        # 컨테이너 이름 패턴
        job_name_patterns = ['job-', 'batch-', 'etl-', 'backup-', 'cron-']
        if any(container.name.startswith(pattern) for pattern in job_name_patterns):
            return True
        
        # 이미지 패턴
        image_tags = container.image.tags if container.image.tags else []
        job_image_patterns = ['job', 'batch', 'etl', 'backup']
        if any(any(pattern in tag for pattern in job_image_patterns) for tag in image_tags):
            return True
        
        return False
    
    def _start_tracking_container(self, container):
        """컨테이너 Job 추적 시작"""
        try:
            labels = container.labels or {}
            
            # Job 정보 추출
            job_info = {
                "name": labels.get('job.name', container.name),
                "type": labels.get('job.type', 'CONTAINER'),
                "description": labels.get('job.description', f"Container job: {container.name}"),
                "container_id": container.id,
                "container_name": container.name,
                "image": container.image.tags[0] if container.image.tags else 'unknown',
                "user": labels.get('job.user', labels.get('user', 'unknown')),
                "hostname": container.name,
                "started_at": datetime.now().isoformat(),
                "environment": dict(container.attrs.get('Config', {}).get('Env', []))
            }
            
            # 중앙 DB에 등록
            run_id = self.tracker.register_job_start(job_info)
            self.tracked_containers[container.id] = {
                'run_id': run_id,
                'container': container,
                'start_time': time.time()
            }
            
            print(f"Started tracking container job: {container.name} (run_id: {run_id})")
            
            # 별도 스레드에서 컨테이너 완료 대기
            threading.Thread(
                target=self._wait_for_container_completion,
                args=(container.id,),
                daemon=True
            ).start()
            
        except Exception as e:
            print(f"Error starting container tracking: {e}")
    
    def _wait_for_container_completion(self, container_id: str):
        """컨테이너 완료 대기"""
        try:
            if container_id not in self.tracked_containers:
                return
            
            container_info = self.tracked_containers[container_id]
            container = container_info['container']
            
            # 컨테이너 완료까지 대기
            result = container.wait()
            exit_code = result['StatusCode']
            
            # 로그 수집
            try:
                logs = container.logs().decode('utf-8', errors='ignore')
            except Exception:
                logs = "Failed to retrieve container logs"
            
            # 완료 처리
            run_id = container_info['run_id']
            status = "SUCCESS" if exit_code == 0 else "FAILED"
            
            error_msg = None
            if exit_code != 0:
                error_msg = f"Container exited with code {exit_code}"
            
            self.tracker.register_job_completion(
                run_id, status, 
                error=error_msg,
                logs=logs
            )
            
            print(f"Container job completed: {container.name} (status: {status})")
            
        except Exception as e:
            print(f"Error waiting for container completion: {e}")
        finally:
            # 추적 목록에서 제거
            if container_id in self.tracked_containers:
                del self.tracked_containers[container_id]
    
    def _finish_tracking_container(self, container_id: str):
        """컨테이너 추적 완료 처리"""
        if container_id in self.tracked_containers:
            container_info = self.tracked_containers[container_id]
            run_id = container_info['run_id']
            
            # 강제 종료된 경우 처리
            self.tracker.register_job_completion(
                run_id, "CANCELLED",
                error="Container was forcefully stopped or removed"
            )
            
            del self.tracked_containers[container_id]
            print(f"Finished tracking container: {container_id}")

def start_container_monitoring(api_url: str = "http://localhost:8000", 
                             api_token: str = None,
                             poll_interval: int = 5):
    """컨테이너 모니터링 시작 (편의 함수)"""
    tracker = JobTracker(api_url, api_token)
    monitor = ContainerJobMonitor(tracker, poll_interval)
    monitor.start_monitoring()
    return monitor
