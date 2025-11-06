# 시스템 리소스 모니터링 프로그램 - 코드 리뷰 보고서

**작성일**: 2025-11-06
**리뷰 대상**: System Resource Monitoring Application v1.0
**리뷰 범위**: 전체 코드베이스 (백엔드, 프론트엔드, 보안)

---

## 📋 목차

1. [개요](#개요)
2. [🔴 심각한 보안 취약점](#심각한-보안-취약점)
3. [🟡 중간 수준 보안 문제](#중간-수준-보안-문제)
4. [🟢 경미한 보안 문제](#경미한-보안-문제)
5. [코드 품질 문제](#코드-품질-문제)
6. [아키텍처 및 설계 문제](#아키텍처-및-설계-문제)
7. [권장사항 요약](#권장사항-요약)

---

## 개요

이 프로그램은 Python 백엔드와 JavaScript 프론트엔드로 구성된 시스템 모니터링 애플리케이션입니다. 실시간 WebSocket 통신을 통해 시스템 리소스 데이터를 수집하고 시각화합니다.

**주요 구성 요소:**
- Backend: Python (psutil, websockets, reportlab)
- Frontend: HTML/CSS/JavaScript (Chart.js)
- 통신: WebSocket (포트 8765), HTTP (포트 8000)

---

## 🔴 심각한 보안 취약점

### 1. 인증/인가 완전 부재 ⚠️ **CRITICAL**

**위치:**
- `backend/server.py:70-74` (WebSocket 서버)
- `backend/server.py:105-112` (HTTP 서버)

**문제:**
```python
# server.py:70-74
self.ws_server = await websockets.serve(
    self.handle_client,
    "0.0.0.0",  # 모든 인터페이스에서 접근 가능
    self.ws_port
)

# server.py:107
server = HTTPServer(('0.0.0.0', port), HTTPServerHandler)
```

**영향:**
- 네트워크 상의 누구나 WebSocket과 HTTP 서버에 접속 가능
- 시스템의 민감한 정보(프로세스, 네트워크, 디스크 정보) 노출
- 원격에서 시스템 정보 수집 가능

**공격 시나리오:**
1. 공격자가 네트워크 스캔으로 8765, 8000 포트 발견
2. WebSocket 연결하여 실시간 시스템 정보 수신
3. 프로세스 목록, 네트워크 활동 등 민감 정보 획득

**권장사항:**
- API 키 또는 토큰 기반 인증 구현
- 세션 기반 인증 추가
- IP 화이트리스트 구현
- localhost (127.0.0.1)로 바인딩 제한

---

### 2. XSS (Cross-Site Scripting) 취약점 ⚠️ **HIGH**

**위치:**
- `frontend/app.js:432-438` (프로세스 테이블 업데이트)
- `frontend/app.js:444-453` (메모리 프로세스 테이블)

**문제:**
```javascript
// app.js:432-438
row.innerHTML = `
    <td>${idx + 1}</td>
    <td>${proc.name}</td>  // ⚠️ 입력 검증 없음
    <td>${proc.pid}</td>
    <td class="${getClassForValue(proc.cpu_percent)}">${proc.cpu_percent.toFixed(1)}%</td>
    <td>${proc.memory_mb.toFixed(1)}</td>
`;
```

**영향:**
- 악의적인 프로세스 이름을 통한 XSS 공격 가능
- 예: 프로세스 이름이 `<script>alert('XSS')</script>`인 경우

**공격 시나리오:**
```bash
# 공격자가 악의적인 프로세스 실행
python -c "import setproctitle; setproctitle.setproctitle('<img src=x onerror=alert(1)>'); import time; time.sleep(1000)"
```

**권장사항:**
- `textContent` 사용 또는 HTML 이스케이프 함수 구현
- Content Security Policy (CSP) 헤더 추가
- 입력 검증 및 새니타이제이션

---

### 3. 무제한 WebSocket 연결 허용 (DoS) ⚠️ **HIGH**

**위치:** `backend/server.py:25-28`

**문제:**
```python
async def register_client(self, websocket):
    """클라이언트 등록"""
    self.clients.add(websocket)  # ⚠️ 연결 수 제한 없음
    print(f"Client connected. Total clients: {len(self.clients)}")
```

**영향:**
- 무제한 WebSocket 연결로 리소스 고갈
- DoS(Denial of Service) 공격에 취약
- 메모리 및 CPU 리소스 소진

**공격 시나리오:**
```python
# 공격 스크립트
import asyncio
import websockets

async def attack():
    tasks = [websockets.connect('ws://target:8765') for _ in range(10000)]
    await asyncio.gather(*tasks)
```

**권장사항:**
- 최대 동시 연결 수 제한 (예: 10개)
- Rate limiting 구현
- Connection timeout 설정
- IP당 연결 수 제한

---

### 4. 커맨드 라인 인자 검증 부재 ⚠️ **MEDIUM-HIGH**

**위치:** `main.py:233-238`

**문제:**
```python
if len(sys.argv) > 1:
    try:
        duration = int(sys.argv[1])  # ⚠️ 범위 검증 없음
        print(f"모니터링 시간: {duration}초로 설정됨")
    except ValueError:
        print("⚠️  잘못된 인자입니다. 기본값(300초) 사용")
```

**영향:**
- 음수 또는 극단적으로 큰 값 입력 가능
- 예: `python main.py -1` 또는 `python main.py 999999999`
- 시스템 리소스 고갈 또는 예상치 못한 동작

**권장사항:**
```python
MIN_DURATION = 10
MAX_DURATION = 3600

if len(sys.argv) > 1:
    try:
        duration = int(sys.argv[1])
        if not MIN_DURATION <= duration <= MAX_DURATION:
            raise ValueError(f"Duration must be between {MIN_DURATION} and {MAX_DURATION}")
    except ValueError as e:
        print(f"⚠️  {e}. 기본값(300초) 사용")
        duration = 300
```

---

### 5. 경로 조작 (Path Traversal) 취약점 ⚠️ **MEDIUM**

**위치:** `backend/pdf_generator.py:33`

**문제:**
```python
def generate_report(self, output_path: str):
    """PDF 리포트 생성"""
    doc = SimpleDocTemplate(
        output_path,  # ⚠️ 경로 검증 없음
        pagesize=A4,
        ...
    )
```

**영향:**
- 임의의 파일 시스템 경로에 PDF 작성 가능
- 예: `../../etc/shadow.pdf`

**공격 시나리오:**
```python
# 악의적인 경로 지정
report_path = "../../../../tmp/malicious.pdf"
generator.generate_report(report_path)
```

**권장사항:**
- 출력 경로를 `reports/` 디렉토리로 제한
- 경로 검증 및 정규화
- `os.path.abspath()`와 `os.path.commonpath()` 사용

---

## 🟡 중간 수준 보안 문제

### 6. 민감 정보 노출

**위치:**
- `backend/monitor.py:165-193` (프로세스 정보)
- `backend/monitor.py:195-205` (시스템 정보)

**문제:**
```python
def get_system_info(self) -> Dict[str, Any]:
    return {
        "platform": platform.system(),
        "platform_version": platform.version(),  # 상세 버전 노출
        "hostname": platform.node(),  # 호스트명 노출
        ...
    }
```

**영향:**
- 시스템 버전, 호스트명 등 민감 정보 노출
- 공격자가 취약점 탐색에 활용 가능
- 프로세스 목록을 통한 실행 중인 서비스 파악

**권장사항:**
- 필수 정보만 노출
- 프로덕션 환경에서는 상세 정보 마스킹
- 로깅 시 민감 정보 필터링

---

### 7. CORS 설정 부재

**위치:** `backend/server.py:93-112`

**문제:**
```python
class HTTPServerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='frontend', **kwargs)

    # ⚠️ CORS 헤더 없음
```

**영향:**
- 기본적으로 Same-Origin Policy만 적용
- 필요한 경우 적절한 CORS 설정 부재

**권장사항:**
```python
def end_headers(self):
    self.send_header('Access-Control-Allow-Origin', 'http://localhost:8000')
    self.send_header('Access-Control-Allow-Methods', 'GET, POST')
    super().end_headers()
```

---

### 8. 예외 처리 미흡

**위치:** 다수 (bare except 사용)

**문제:**
```python
# monitor.py:26-28
try:
    self.disk_io_start[disk.device] = psutil.disk_io_counters(perdisk=True)
except:  # ⚠️ bare except
    pass

# monitor.py:50-51
except:  # ⚠️ bare except
    pass
```

**영향:**
- 중요한 예외 정보 손실
- 디버깅 어려움
- 보안 관련 예외 무시 가능

**권장사항:**
```python
except (PermissionError, OSError) as e:
    logging.warning(f"Failed to access disk IO: {e}")
except Exception as e:
    logging.error(f"Unexpected error: {e}")
```

---

### 9. 에러 메시지 정보 노출

**위치:**
- `backend/data_collector.py:42`
- `backend/data_collector.py:81`

**문제:**
```python
except Exception as e:
    print(f"Callback error: {e}")  # ⚠️ 상세 에러 콘솔 출력

except Exception as e:
    print(f"Collection error: {e}")  # ⚠️ 상세 에러 노출
```

**영향:**
- 스택 트레이스를 통한 내부 구조 노출
- 공격자에게 유용한 정보 제공

**권장사항:**
- 로깅 시스템 사용 (logging 모듈)
- 운영 환경에서는 간단한 에러 메시지만 표시
- 상세 로그는 파일에만 기록

---

### 10. WebSocket 메시지 크기 제한 없음

**위치:** `backend/server.py:35-45`

**문제:**
```python
async def handle_client(self, websocket, path):
    await self.register_client(websocket)
    try:
        async for message in websocket:  # ⚠️ 메시지 크기 제한 없음
            print(f"Received message: {message}")
```

**영향:**
- 대용량 메시지로 메모리 고갈
- DoS 공격 가능

**권장사항:**
```python
async for message in websocket:
    if len(message) > 1024 * 1024:  # 1MB 제한
        await websocket.close(1009, "Message too large")
        return
```

---

## 🟢 경미한 보안 문제

### 11. HTTP 서버 디렉토리 리스팅

**위치:** `backend/server.py:93-98`

**문제:**
```python
class HTTPServerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='frontend', **kwargs)
        # SimpleHTTPRequestHandler는 기본적으로 디렉토리 리스팅 허용
```

**권장사항:**
- 디렉토리 리스팅 비활성화
- 인덱스 파일만 서빙

---

### 12. 로그 출력 억제

**위치:** `backend/server.py:100-102`

**문제:**
```python
def log_message(self, format, *args):
    """로그 메시지 커스터마이징"""
    pass  # ⚠️ 로그 완전 억제
```

**영향:**
- 보안 이벤트 추적 불가
- 감사 로그 부재

**권장사항:**
- 적절한 로깅 시스템 구현
- 중요 이벤트는 로그 파일에 기록

---

### 13. 외부 CDN 의존성

**위치:** `frontend/index.html:8`

**문제:**
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

**영향:**
- CDN 장애 시 기능 작동 불가
- CDN 해킹 시 악성 코드 삽입 위험
- Supply Chain Attack 가능성

**권장사항:**
- 라이브러리 로컬에 호스팅
- Subresource Integrity (SRI) 해시 사용

---

## 코드 품질 문제

### 14. 하드코딩된 설정값

**위치:** 여러 곳

**문제:**
```python
# server.py:18-20
def __init__(self, ws_port: int = 8765, http_port: int = 8000):
    self.ws_port = ws_port
    self.http_port = http_port

# data_collector.py:14
const MAX_DATA_POINTS = 300;
```

**권장사항:**
- 설정 파일 (config.yaml, .env) 사용
- 환경 변수로 설정 관리

---

### 15. 동시성 문제 가능성

**위치:** `backend/data_collector.py:26`

**문제:**
```python
self.collected_data: List[Dict[str, Any]] = []  # 스레드 안전하지 않음
```

**영향:**
- 멀티스레드 환경에서 데이터 경합 가능
- 데이터 손실 또는 일관성 문제

**권장사항:**
```python
import threading
self.collected_data = []
self.data_lock = threading.Lock()

# 사용 시
with self.data_lock:
    self.collected_data.append(data)
```

---

### 16. 메모리 누수 가능성

**위치:** `backend/server.py:21`

**문제:**
```python
self.clients: Set = set()  # 연결 끊김 클라이언트 정리 로직 불완전
```

**영향:**
- 장시간 실행 시 메모리 증가
- 좀비 연결 누적

**권장사항:**
- 주기적인 연결 상태 확인
- Heartbeat/Ping-Pong 메커니즘 구현

---

### 17. 타입 힌트 불완전

**문제:**
```python
# server.py:21
self.clients: Set = set()  # ⚠️ Set[websockets.WebSocketServerProtocol]
```

**권장사항:**
```python
from typing import Set
import websockets

self.clients: Set[websockets.WebSocketServerProtocol] = set()
```

---

## 아키텍처 및 설계 문제

### 18. 관심사 분리 부족

**문제:**
- `main.py`에 너무 많은 로직 집중
- 설정 관리 분리 필요

**권장사항:**
- Config 클래스 분리
- 의존성 주입 패턴 적용

---

### 19. 테스트 코드 부재

**영향:**
- 보안 패치 적용 시 리그레션 위험
- 코드 변경 검증 어려움

**권장사항:**
- 단위 테스트 작성 (pytest)
- 통합 테스트 추가
- 보안 테스트 자동화

---

### 20. 로깅 시스템 부재

**문제:**
- `print()` 함수만 사용
- 로그 레벨, 로테이션 없음

**권장사항:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler()
    ]
)
```

---

## 권장사항 요약

### 즉시 조치 필요 (P0 - Critical)

1. ✅ **인증/인가 시스템 구현**
   - API 키 또는 토큰 기반 인증
   - localhost 바인딩으로 제한

2. ✅ **XSS 방어**
   - HTML 이스케이프 함수 구현
   - CSP 헤더 추가

3. ✅ **DoS 방어**
   - 연결 수 제한
   - Rate limiting 구현

4. ✅ **입력 검증**
   - 모든 사용자 입력 검증
   - 범위 체크 추가

---

### 단기 조치 (P1 - High)

5. ✅ **예외 처리 개선**
   - Specific exception 사용
   - 적절한 로깅

6. ✅ **민감 정보 보호**
   - 정보 노출 최소화
   - 마스킹 적용

7. ✅ **보안 헤더 추가**
   - CORS 설정
   - Security headers

---

### 중기 조치 (P2 - Medium)

8. ✅ **로깅 시스템 구현**
9. ✅ **설정 관리 개선**
10. ✅ **테스트 코드 작성**

---

### 장기 조치 (P3 - Low)

11. ✅ **코드 리팩토링**
12. ✅ **문서화 개선**
13. ✅ **성능 최적화**

---

## 보안 체크리스트

### 인증/인가
- [ ] API 키 인증 구현
- [ ] 세션 관리 구현
- [ ] IP 화이트리스트

### 입력 검증
- [ ] 모든 입력 검증
- [ ] 파일 경로 검증
- [ ] WebSocket 메시지 검증

### 출력 인코딩
- [ ] HTML 이스케이프
- [ ] JSON 직렬화 검증
- [ ] SQL 인젝션 방어 (해당 없음)

### 암호화
- [ ] HTTPS/WSS 사용
- [ ] 민감 데이터 암호화

### 로깅/모니터링
- [ ] 보안 이벤트 로깅
- [ ] 감사 로그 구현
- [ ] 이상 탐지

### 에러 처리
- [ ] 안전한 에러 처리
- [ ] 정보 노출 방지
- [ ] Graceful degradation

---

## 참고 자료

### 보안 표준
- OWASP Top 10
- CWE (Common Weakness Enumeration)
- SANS Top 25

### Python 보안
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [Bandit Security Linter](https://github.com/PyCQA/bandit)

### WebSocket 보안
- [WebSocket Security](https://owasp.org/www-community/vulnerabilities/WebSocket_Security)

---

## 결론

이 애플리케이션은 기능적으로는 잘 작동하지만, **프로덕션 환경에서 사용하기에는 심각한 보안 취약점**이 다수 존재합니다.

**핵심 문제:**
1. 인증/인가 시스템 완전 부재
2. 모든 네트워크 인터페이스에 바인딩 (0.0.0.0)
3. 입력 검증 미흡
4. XSS 취약점
5. DoS 공격에 취약

**권장 사용 환경:**
- ✅ 로컬 개발/테스트 환경
- ✅ 격리된 네트워크 환경
- ❌ 공개 네트워크 (인터넷)
- ❌ 프로덕션 환경 (보안 패치 전)

**보안 개선 후 사용 가능:**
최소한 P0, P1 조치사항을 완료한 후 프로덕션 배포를 권장합니다.

---

**리뷰어:** AI Code Reviewer
**리뷰 일자:** 2025-11-06
**버전:** v1.0
