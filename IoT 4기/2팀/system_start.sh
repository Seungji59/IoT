#!/bin/bash

# 졸음운전 방지 시스템 - HDMI 디스플레이 모드
# X11 디스플레이 권한 설정 포함

export DISPLAY=:0
export XAUTHORITY=/home/admin/.Xauthority

echo "═══════════════════════════════════════════"
echo "🚗 졸음운전 방지 시스템 시작"
echo "═══════════════════════════════════════════"
echo ""
echo "📺 디스플레이 설정:"
echo "   DISPLAY=$DISPLAY"
echo "   XAUTHORITY=$XAUTHORITY"
echo ""
echo "🎥 카메라:"
echo "   - 얼굴 감지: Picamera2 카메라 0"
echo "   - 차선 감지: Picamera2 카메라 1"
echo ""
echo "🎮 조작방법:"
echo "   - 토글 스위치: GPIO 17 (방향 지시등 LEFT / OFF / RIGHT)"
echo "   - 'q' 키: 프로그램 종료"
echo ""
echo "⏱️ 시스템 시작 대기 중..."
sleep 2

cd /home/admin/k-digital
/home/admin/k-digital/env/bin/python -u hyuk/main.py

echo ""
echo "✅ 시스템 종료되었습니다."
