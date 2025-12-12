#!/usr/bin/env python3
"""
ETL Job 예시 - 데이터 추출, 변환, 적재
"""
import pandas as pd
import sys
import time
import random
from datetime import datetime

def extract_data():
    """데이터 추출 시뮬레이션"""
    print(f"[{datetime.now()}] Starting data extraction...")
    
    # 가상의 데이터 생성
    data = {
        'id': range(1, 1001),
        'name': [f'User_{i}' for i in range(1, 1001)],
        'value': [random.randint(1, 100) for _ in range(1000)],
        'status': [random.choice(['active', 'inactive', None]) for _ in range(1000)]
    }
    
    df = pd.DataFrame(data)
    print(f"[{datetime.now()}] Extracted {len(df)} records")
    return df

def transform_data(df):
    """데이터 변환"""
    print(f"[{datetime.now()}] Starting data transformation...")
    
    # 결측값 처리
    df['status'] = df['status'].fillna('unknown')
    
    # 데이터 필터링
    df_clean = df[df['value'] > 10]
    
    # 새로운 컬럼 추가
    df_clean['processed_at'] = datetime.now()
    
    print(f"[{datetime.now()}] Transformed data: {len(df_clean)} records after cleaning")
    return df_clean

def load_data(df):
    """데이터 적재 시뮬레이션"""
    print(f"[{datetime.now()}] Starting data loading...")
    
    # 파일로 저장 (실제로는 DB에 저장)
    output_file = '/tmp/etl_output.csv'
    df.to_csv(output_file, index=False)
    
    print(f"[{datetime.now()}] Data loaded to {output_file}")
    return output_file

def main():
    try:
        print("="*50)
        print("ETL Job Started")
        print("="*50)
        
        # Extract
        raw_data = extract_data()
        time.sleep(1)  # 처리 시간 시뮬레이션
        
        # Transform
        clean_data = transform_data(raw_data)
        time.sleep(1)
        
        # Load
        output_file = load_data(clean_data)
        time.sleep(1)
        
        print("="*50)
        print("ETL Job Completed Successfully")
        print(f"Output: {output_file}")
        print("="*50)
        
        return 0
        
    except Exception as e:
        print(f"ERROR: ETL Job failed - {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
