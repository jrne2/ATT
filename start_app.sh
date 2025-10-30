#!/bin/bash

# 1. 가상 환경 활성화 (경로 확인)
echo "Activating virtual environment..."
source /home/ec2-user/proj/ATT/.venv/bin/activate

# 2. Streamlit 앱을 백그라운드(&)에서 실행
echo "Starting Streamlit app in background..."
streamlit run /home/ec2-user/proj/ATT/app.py --server.port 8501 --server.address 0.0.0.0 &

# 3. Streamlit이 켜질 때까지 5초 대기
echo "Waiting 5 seconds for Streamlit to start..."
sleep 5

# 4. Cloudflare 터널을 포그라운드에서 실행 (이게 꺼지면 스크립트 종료)
echo "Starting Cloudflare tunnel..."
cloudflared tunnel --url http://localhost:8501