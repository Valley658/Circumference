from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncio
from decimal import Decimal, getcontext
import uvicorn
from datetime import datetime

app = FastAPI()

# 원주율 계산 상태
pi_state = {
    "current_pi": "3.14159",
    "iterations": 0,
    "method": "Chudnovsky Algorithm",
    "digits": 5
}

# HTML 페이지
html = """
<!DOCTYPE html>
<html>
<head>
    <title>원주율 실시간 계산</title>
    <style>
        html, body {
            margin: 0;
            padding: 0;
            height: 100%;
            overflow-y: auto;
        }
        body {
            font-family: 'Courier New', monospace;
            background: #000;
            color: #0f0;
            padding: 20px;
            font-size: 1.5em;
            line-height: 1.8;
            word-wrap: break-word;
        }
        .pi-display {
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
    <div class="pi-display" id="pi-value">계산 시작 대기 중...</div>

    <script>
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        const piValueDiv = document.getElementById('pi-value');

        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            piValueDiv.textContent = data.current_pi;
        };
        
        // 페이지 로드 시 맨 위로 스크롤
        window.onload = function() {
            window.scrollTo(0, 0);
        };
    </script>
</body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌐 클라이언트 연결됨")
    
    try:
        # Bailey-Borwein-Plouffe (BBP) 공식으로 원주율 계산
        await calculate_pi_bbp(websocket)
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 에러 발생: {e}")
    finally:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔌 클라이언트 연결 종료")

async def calculate_pi_bbp(websocket: WebSocket):
    """Bailey-Borwein-Plouffe 공식으로 원주율 계산"""
    print(f"\n{'='*80}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 원주율 계산 시작!")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📐 사용 알고리즘: Bailey-Borwein-Plouffe (BBP) Formula")
    print(f"{'='*80}\n")
    
    # 무한 정밀도 설정 - 메모리가 허용하는 한 계속 증가
    getcontext().prec = 100000  # 초기 정밀도 100,000자리
    
    pi = Decimal(0)
    k = 0
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  원주율은 무리수로 마지막 숫자가 없습니다.")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 시스템이 허용하는 한 무한히 계속 계산합니다...")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 💡 중지하려면 브라우저를 닫으세요.\n")
    
    while True:
        # BBP 공식: π = Σ[k=0 to ∞] (1/16^k) * (4/(8k+1) - 2/(8k+4) - 1/(8k+5) - 1/(8k+6))
        term1 = Decimal(4) / Decimal(8 * k + 1)
        term2 = Decimal(2) / Decimal(8 * k + 4)
        term3 = Decimal(1) / Decimal(8 * k + 5)
        term4 = Decimal(1) / Decimal(8 * k + 6)
        
        series_term = term1 - term2 - term3 - term4
        power_term = Decimal(1) / (Decimal(16) ** k)
        
        current_term = power_term * series_term
        pi += current_term
        
        # 정밀도 동적 증가 (필요시 자동으로 증가)
        if k > 0 and k % 1000 == 0:
            current_prec = getcontext().prec
            getcontext().prec = current_prec + 10000
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📈 정밀도 증가: {current_prec} → {getcontext().prec}")
        
        # 콘솔 로그 (10번마다)
        if k % 10 == 0:
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            print(f"[{timestamp}] 반복 #{k+1:4d} | "
                  f"항: {float(current_term):.15e} | "
                  f"현재 π: {str(pi)[:50]}...")
        
        if k % 50 == 0:  # 50번마다 상세 로그
            print(f"           └─> 4/(8k+1)={float(term1):.6f}, "
                  f"2/(8k+4)={float(term2):.6f}, "
                  f"1/(8k+5)={float(term3):.6f}, "
                  f"1/(8k+6)={float(term4):.6f}")
        
        # 웹소켓으로 전송
        pi_str = str(pi)[:min(100 + k, len(str(pi)))]
        
        pi_state["current_pi"] = pi_str
        pi_state["iterations"] = k + 1
        pi_state["digits"] = len(pi_str) - 1  # 소수점 제외
        pi_state["method"] = "BBP Formula"
        
        try:
            await websocket.send_json(pi_state)
        except:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  클라이언트 연결 끊김")
            break
        
        k += 1
        
        # 더 빠른 업데이트를 위해 짧은 딜레이
        if k % 5 == 0:  # 5번마다 웹소켓 업데이트
            await asyncio.sleep(0.01)
    
    print(f"\n{'='*80}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 계산 완료!")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 최종 반복 횟수: {k}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📏 계산된 자릿수: {len(str(pi))-1}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 최종 π 값: {str(pi)[:100]}...")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    print("="*80)
    print("🚀 FastAPI 원주율 계산 서버 시작")
    print("="*80)
    print("📍 서버 주소: http://localhost:5000")
    print("💡 브라우저에서 http://localhost:5000 를 열어주세요")
    print("="*80)
    uvicorn.run(app, host="127.0.0.1", port=5000)
