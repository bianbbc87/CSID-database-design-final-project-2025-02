#!/usr/bin/env python3
"""
백업 Job 예시 - 의도적 실패 시나리오 포함
"""
import os
import sys
import time
import random
from datetime import datetime

def check_disk_space():
    """디스크 공간 확인"""
    print(f"[{datetime.now()}] Checking disk space...")
    
    # 30% 확률로 디스크 공간 부족 시뮬레이션
    if random.random() < 0.3:
        raise Exception("Insufficient disk space: only 500MB available, need 2GB")
    
    print(f"[{datetime.now()}] Disk space OK: 10GB available")

def backup_database():
    """데이터베이스 백업"""
    print(f"[{datetime.now()}] Starting database backup...")
    
    # 백업 진행 시뮬레이션
    databases = ['users_db', 'orders_db', 'analytics_db']
    
    for db in databases:
        print(f"[{datetime.now()}] Backing up {db}...")
        time.sleep(1)  # 백업 시간 시뮬레이션
        
        # 20% 확률로 개별 DB 백업 실패
        if random.random() < 0.2:
            raise Exception(f"Failed to backup {db}: connection timeout")
        
        print(f"[{datetime.now()}] {db} backup completed")

def backup_files():
    """파일 백업"""
    print(f"[{datetime.now()}] Starting file backup...")
    
    file_paths = ['/app/logs', '/app/config', '/app/uploads']
    
    for path in file_paths:
        print(f"[{datetime.now()}] Backing up {path}...")
        time.sleep(0.5)
        
        # 파일 백업은 항상 성공
        print(f"[{datetime.now()}] {path} backup completed")

def verify_backup():
    """백업 검증"""
    print(f"[{datetime.now()}] Verifying backup integrity...")
    time.sleep(1)
    
    # 10% 확률로 검증 실패
    if random.random() < 0.1:
        raise Exception("Backup verification failed: checksum mismatch")
    
    print(f"[{datetime.now()}] Backup verification passed")

def cleanup_old_backups():
    """오래된 백업 정리"""
    print(f"[{datetime.now()}] Cleaning up old backups...")
    
    # 7일 이상 된 백업 삭제 시뮬레이션
    old_backups = ['backup_2024-12-01.tar.gz', 'backup_2024-12-02.tar.gz']
    
    for backup in old_backups:
        print(f"[{datetime.now()}] Removing old backup: {backup}")
        time.sleep(0.2)
    
    print(f"[{datetime.now()}] Cleanup completed")

def main():
    try:
        print("="*50)
        print("Daily Backup Job Started")
        print("="*50)
        
        # 1. 디스크 공간 확인
        check_disk_space()
        
        # 2. 데이터베이스 백업
        backup_database()
        
        # 3. 파일 백업
        backup_files()
        
        # 4. 백업 검증
        verify_backup()
        
        # 5. 오래된 백업 정리
        cleanup_old_backups()
        
        print("="*50)
        print("Backup Job Completed Successfully")
        print(f"Backup location: /backups/{datetime.now().strftime('%Y-%m-%d')}")
        print("="*50)
        
        return 0
        
    except Exception as e:
        print(f"ERROR: Backup Job failed - {str(e)}")
        print(f"[{datetime.now()}] Rolling back partial backup...")
        
        # 실패 시 스택 트레이스 출력
        import traceback
        traceback.print_exc()
        
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
