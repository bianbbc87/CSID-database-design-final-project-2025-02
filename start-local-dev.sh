#!/bin/bash

# CSID Job Management System - Local Development Environment
echo "🚀 Starting CSID Job Management System - Local Development"

# 프로젝트 루트 디렉토리로 이동
cd "$(dirname "$0")"

# MySQL과 컨테이너 모니터 실행
echo "📦 Starting MySQL database and Container Monitor..."
docker-compose -f docker-compose-with-jobs.yml up -d mysql container_monitor

# 데이터베이스 준비 대기
echo "⏳ Waiting for database to be ready..."
sleep 10

# 백엔드 실행 (가상환경)
echo "🔧 Starting Backend API..."
source venv/bin/activate
export DATABASE_URL="mysql+pymysql://root:password@localhost:3340/job_management"
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# 프론트엔드 실행
echo "🎨 Starting Frontend..."
cd frontend
REACT_APP_API_URL=http://localhost:8000 npm start &
FRONTEND_PID=$!
cd ..

echo "✅ Development environment started!"
echo "📊 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo "🗄️ Database: localhost:3340"
echo "🔍 Container Monitor: Running in Docker (auto-detects docker run containers)"
echo ""
echo "💡 Now you can run 'docker run' commands and they will be automatically tracked!"
echo "Press Ctrl+C to stop all services"

# 종료 시그널 처리
cleanup() {
    echo "🛑 Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    docker-compose -f docker-compose-with-jobs.yml stop mysql container_monitor
    exit 0
}

trap cleanup SIGINT SIGTERM

# 백그라운드 프로세스 대기
wait
