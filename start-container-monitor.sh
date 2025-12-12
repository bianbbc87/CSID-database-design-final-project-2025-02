#!/bin/bash

echo "🔍 Starting Container Monitor..."

# 프로젝트 루트로 이동
cd "$(dirname "$0")"

# 가상환경 활성화
source venv/bin/activate

# 필요한 패키지 설치
pip install requests pytz

echo "👀 Monitoring all Docker containers for automatic registration"
echo "🔄 Will check every 30 seconds for completed containers"
echo "⏹️ Press Ctrl+C to stop"
echo ""

# 컨테이너 모니터 실행
python backend/container_monitor.py
