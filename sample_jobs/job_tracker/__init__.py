"""
Job Tracker - 자동 Job 추적 라이브러리

기존 코드에 최소한의 수정으로 Job 실행을 자동 추적하고 중앙 DB에 기록합니다.

사용법:
    from job_tracker import track_job
    
    @track_job(job_type="ETL", description="Daily data processing")
    def my_job():
        # 기존 코드 그대로
        pass
"""

from .tracker import (
    track_job,
    set_tracker_config,
    manual_job_start,
    manual_job_complete,
    JobTracker
)

from .container_monitor import (
    ContainerJobMonitor,
    start_container_monitoring
)

__version__ = "1.0.0"
__all__ = [
    'track_job',
    'set_tracker_config', 
    'manual_job_start',
    'manual_job_complete',
    'JobTracker',
    'ContainerJobMonitor',
    'start_container_monitoring'
]
