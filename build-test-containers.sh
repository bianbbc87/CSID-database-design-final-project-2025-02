#!/bin/bash

echo "🐳 Building test containers..."

cd "$(dirname "$0")/sample_jobs"

# 1. 성공 컨테이너 빌드
echo "📦 Building test-success container..."
docker build -t test-job-success ./test-success

# 2. 실패 컨테이너 빌드  
echo "📦 Building test-failure container..."
docker build -t test-job-failure ./test-failure

# 3. 긴 실행 컨테이너 빌드
echo "📦 Building test-long container..."
docker build -t test-job-long ./test-long

echo "✅ All test containers built successfully!"
echo ""
echo "🚀 Usage examples:"
echo "  docker run --name job-success test-job-success"
echo "  docker run --name job-failure test-job-failure" 
echo "  docker run --name job-long test-job-long"
echo ""
echo "💡 Tip: Use these containers in your Job Management System!"
