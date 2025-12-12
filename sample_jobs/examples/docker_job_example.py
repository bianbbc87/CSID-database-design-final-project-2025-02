#!/usr/bin/env python3
"""
Docker 컨테이너에서 실행되는 Job 예시

컨테이너 라벨을 통해 자동으로 Job으로 인식되고 추적됩니다.
"""

import time
import random
import os
from datetime import datetime

def container_etl_job():
    """컨테이너에서 실행되는 ETL Job"""
    print(f"[{datetime.now()}] Container ETL Job Started")
    print(f"Container ID: {os.environ.get('HOSTNAME', 'unknown')}")
    print(f"Job User: {os.environ.get('JOB_USER', 'container-user')}")
    
    # 데이터 처리 시뮬레이션
    steps = [
        "Connecting to data source...",
        "Extracting customer data...",
        "Extracting order data...", 
        "Joining datasets...",
        "Applying business rules...",
        "Validating data quality...",
        "Loading to data warehouse...",
        "Updating metadata..."
    ]
    
    for i, step in enumerate(steps, 1):
        print(f"[{datetime.now()}] Step {i}/{len(steps)}: {step}")
        time.sleep(random.uniform(0.5, 2.0))
        
        # 5% 확률로 각 단계에서 실패
        if random.random() < 0.05:
            raise Exception(f"Failed at step {i}: {step}")
    
    print(f"[{datetime.now()}] ETL Job completed successfully")
    print("Processed 50,000 customer records")
    print("Processed 125,000 order records") 
    print("Data quality score: 98.5%")

def main():
    try:
        container_etl_job()
        print("EXIT_CODE: 0")
    except Exception as e:
        print(f"ERROR: {e}")
        print("EXIT_CODE: 1")
        exit(1)

if __name__ == "__main__":
    main()
