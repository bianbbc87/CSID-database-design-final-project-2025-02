#!/bin/bash

# Frontend only startup script
echo "🎨 Starting Frontend only..."

cd "$(dirname "$0")"

# 프론트엔드 실행
cd frontend
REACT_APP_API_URL=http://localhost:8001 npm start
