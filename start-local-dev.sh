#!/bin/bash

# CSID Job Management System - Local Development Environment
echo "🚀 Starting CSID Job Management System - Local Development"

# 프로젝트 루트 디렉토리로 이동
cd "$(dirname "$0")"

# 기존 프로세스 정리
echo "🧹 Cleaning up existing processes..."
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "npm start" 2>/dev/null || true

# MySQL 컨테이너 시작
echo "📦 Starting MySQL database..."
docker-compose -f docker-compose-with-jobs.yml up -d mysql

# 데이터베이스 준비 대기
echo "⏳ Waiting for database to be ready..."
sleep 8

# 로그 디렉토리 생성
mkdir -p logs

# 백엔드 실행 (가상환경)
echo "🔧 Starting Backend API..."
source venv/bin/activate
export DATABASE_URL="mysql+pymysql://root:password@localhost:3340/job_management"
cd backend
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# 백엔드 시작 대기
echo "⏳ Waiting for backend to start..."
sleep 3

# Container Monitor 실행
echo "🔍 Starting Container Monitor..."
nohup python backend/container_monitor.py > logs/monitor.log 2>&1 &
MONITOR_PID=$!

# 프론트엔드 실행 (선택사항)
read -p "🎨 Start Frontend? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🎨 Starting Frontend..."
    cd frontend
    REACT_APP_API_URL=http://localhost:8000 nohup npm start > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
else
    FRONTEND_PID=""
fi

echo ""
echo "✅ Development environment started!"
echo "📊 Backend API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo "🗄️ Database: localhost:3340"
echo "🔍 Container Monitor: Running (logs/monitor.log)"
if [[ ! -z "$FRONTEND_PID" ]]; then
    echo "🎨 Frontend: http://localhost:3000 (logs/frontend.log)"
fi
echo ""
echo "📋 View logs:"
echo "  Backend:  tail -f logs/backend.log"
echo "  Monitor:  tail -f logs/monitor.log"
if [[ ! -z "$FRONTEND_PID" ]]; then
    echo "  Frontend: tail -f logs/frontend.log"
fi
echo ""
echo "💡 Now you can run 'docker run' commands and they will be automatically tracked!"
echo "Press Ctrl+C to stop all services"

# PID 파일 저장
echo $BACKEND_PID > logs/backend.pid
echo $MONITOR_PID > logs/monitor.pid
if [[ ! -z "$FRONTEND_PID" ]]; then
    echo $FRONTEND_PID > logs/frontend.pid
fi

# 종료 시그널 처리
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    
    # PID 파일에서 프로세스 종료
    if [ -f logs/backend.pid ]; then
        kill $(cat logs/backend.pid) 2>/dev/null || true
        rm logs/backend.pid
    fi
    
    if [ -f logs/monitor.pid ]; then
        kill $(cat logs/monitor.pid) 2>/dev/null || true
        rm logs/monitor.pid
    fi
    
    if [ -f logs/frontend.pid ]; then
        kill $(cat logs/frontend.pid) 2>/dev/null || true
        rm logs/frontend.pid
    fi
    
    # Docker 컨테이너 정지
    docker-compose -f docker-compose-with-jobs.yml stop mysql
    
    echo "✅ All services stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 백그라운드 프로세스 대기
echo "🔄 Services running... (Ctrl+C to stop)"
while true; do
    sleep 1
done
