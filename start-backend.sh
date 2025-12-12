#!/bin/bash

# Backend only startup script
echo "🔧 Starting Backend API only..."

cd "$(dirname "$0")"

# MySQL 컨테이너 실행
echo "📦 Starting MySQL database..."
docker-compose -f docker-compose-with-jobs.yml up -d mysql

# 데이터베이스 준비 대기
echo "⏳ Waiting for database to be ready..."
sleep 10

# 백엔드 실행
echo "🚀 Starting Backend API..."
source venv/bin/activate
export DATABASE_URL="mysql+pymysql://root:password@localhost:3340/job_management"
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
