# CSID-database-design-final-project-2025-02
CSID 데이터베이스 설계 수업 기말 프로젝트

## 🚀 빠른 시작

### 시스템 요구사항
- macOS (M2 기준으로 설정됨)
- Python 가상환경 (venv)

### 설치 및 실행
1. 가상환경 설정 및 의존성 설치
```bash
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

2. 백그라운드 서비스 실행
```bash
# 가상환경에서 실행
python backend/container_monitor.py
python backend/scheduler.sh
```

3. 전체 개발 환경 실행
```bash
./start-local-dev.sh
```