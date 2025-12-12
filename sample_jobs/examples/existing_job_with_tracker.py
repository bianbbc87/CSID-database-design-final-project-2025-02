#!/usr/bin/env python3
"""
기존 Job 코드에 Job Tracker 적용 예시

기존 코드를 거의 수정하지 않고 @track_job 데코레이터만 추가하면
자동으로 중앙 DB에 실행 이력이 기록됩니다.
"""

# 1. Job Tracker 라이브러리 import (추가된 부분)
import sys
import os
sys.path.append('/Users/eunji/Desktop/Project/CSID-database-design-final-project-2025-02')

from job_tracker import track_job, set_tracker_config

# 2. Tracker 설정 (한 번만 설정)
api_url = os.environ.get('JOB_TRACKER_API_URL', 'http://localhost:8000')
set_tracker_config(api_url)

# 3. 기존 코드에 데코레이터만 추가
@track_job(job_type="ETL", description="Daily sales data processing")
def process_sales_data():
    """기존 ETL Job - 코드는 그대로, 데코레이터만 추가"""
    import pandas as pd
    import time
    import random
    
    print("Starting sales data processing...")
    
    # 데이터 로드 시뮬레이션
    print("Loading sales data from database...")
    time.sleep(1)
    
    # 가상 데이터 생성
    data = {
        'date': pd.date_range('2024-01-01', periods=100),
        'sales': [random.randint(1000, 5000) for _ in range(100)],
        'region': [random.choice(['North', 'South', 'East', 'West']) for _ in range(100)]
    }
    df = pd.DataFrame(data)
    print(f"Loaded {len(df)} sales records")
    
    # 데이터 변환
    print("Transforming data...")
    df['sales_category'] = df['sales'].apply(
        lambda x: 'High' if x > 3500 else 'Medium' if x > 2000 else 'Low'
    )
    time.sleep(1)
    
    # 집계
    summary = df.groupby(['region', 'sales_category']).size().reset_index(name='count')
    print("Data transformation completed")
    print(summary.head())
    
    # 결과 저장
    output_file = '/tmp/sales_summary.csv'
    summary.to_csv(output_file, index=False)
    print(f"Results saved to {output_file}")
    
    return f"Processed {len(df)} records, saved to {output_file}"

@track_job(job_type="BACKUP", description="Database backup job")
def backup_database():
    """기존 백업 Job - 실패 시나리오 포함"""
    import time
    import random
    
    print("Starting database backup...")
    
    # 디스크 공간 체크 (30% 확률로 실패)
    if random.random() < 0.3:
        raise Exception("Insufficient disk space: only 500MB available, need 2GB")
    
    print("Disk space check passed")
    time.sleep(1)
    
    # 백업 실행
    databases = ['users', 'orders', 'products', 'analytics']
    for db in databases:
        print(f"Backing up {db} database...")
        time.sleep(0.5)
        
        # 20% 확률로 개별 DB 백업 실패
        if random.random() < 0.2:
            raise Exception(f"Failed to backup {db}: connection timeout")
    
    print("All databases backed up successfully")
    return "Backup completed: 4 databases"

@track_job(job_type="CLEANUP", description="Log file cleanup")
def cleanup_old_logs():
    """기존 정리 Job"""
    import os
    import time
    
    print("Starting log cleanup...")
    
    # 가상의 로그 파일들
    log_files = [
        '/var/log/app1.log.2024-11-01',
        '/var/log/app1.log.2024-11-02', 
        '/var/log/app2.log.2024-11-01',
        '/var/log/error.log.2024-10-30'
    ]
    
    cleaned_count = 0
    for log_file in log_files:
        print(f"Checking {log_file}...")
        # 실제로는 파일 존재 여부와 날짜 확인
        print(f"Removing old log: {log_file}")
        cleaned_count += 1
        time.sleep(0.2)
    
    print(f"Cleanup completed: removed {cleaned_count} old log files")
    return f"Cleaned {cleaned_count} files"

# 4. 기존 실행 코드도 그대로 유지
def main():
    """메인 실행 함수"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python existing_job_with_tracker.py <job_name>")
        print("Available jobs: sales_etl, backup, cleanup")
        return
    
    job_name = sys.argv[1]
    
    try:
        if job_name == "sales_etl":
            result = process_sales_data()
            print(f"ETL Job completed: {result}")
            
        elif job_name == "backup":
            result = backup_database()
            print(f"Backup Job completed: {result}")
            
        elif job_name == "cleanup":
            result = cleanup_old_logs()
            print(f"Cleanup Job completed: {result}")
            
        else:
            print(f"Unknown job: {job_name}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Job failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
