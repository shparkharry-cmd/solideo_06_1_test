#!/usr/bin/env python3
"""
시스템 리소스 모니터링 프로그램
실시간으로 시스템 리소스를 모니터링하고 웹 대시보드에 표시하며 PDF 리포트를 생성합니다.
"""

import os
import sys
import time
import webbrowser
import threading
from datetime import datetime

# 백엔드 모듈 임포트
from backend.monitor import SystemMonitor
from backend.data_collector import DataCollector
from backend.server import WebSocketServer, start_http_server
from backend.pdf_generator import PDFReportGenerator


class SystemMonitorApp:
    """시스템 모니터링 애플리케이션 메인 클래스"""

    def __init__(self, interval=1, duration=300):
        """
        Args:
            interval: 데이터 수집 간격 (초)
            duration: 총 수집 시간 (초)
        """
        self.interval = interval
        self.duration = duration

        # 컴포넌트 초기화
        self.data_collector = DataCollector(interval=interval, duration=duration)
        self.ws_server = WebSocketServer(ws_port=8765, http_port=8000)
        self.http_server = None
        self.http_thread = None

        # PDF 리포트 경로
        self.report_path = None

    def on_data_collected(self, data):
        """데이터 수집 시 호출되는 콜백"""
        # WebSocket으로 데이터 전송
        self.ws_server.send_data(data)

    def start_servers(self):
        """서버들을 시작"""
        print("=" * 60)
        print("시스템 리소스 모니터링 프로그램 시작")
        print("=" * 60)

        # HTTP 서버 시작
        print("\n[1/3] HTTP 서버 시작 중...")
        self.http_server, self.http_thread = start_http_server(8000)
        time.sleep(1)

        # WebSocket 서버 시작
        print("[2/3] WebSocket 서버 시작 중...")
        self.ws_server.start_in_thread()
        time.sleep(1)

        # 데이터 수집기 콜백 등록
        print("[3/3] 데이터 수집기 초기화 중...")
        self.data_collector.add_callback(self.on_data_collected)

        print("\n✅ 모든 서버가 시작되었습니다.")
        print(f"📊 대시보드: http://localhost:8000")
        print(f"⏱️  모니터링 시간: {self.duration}초 ({self.duration // 60}분)")
        print()

    def open_browser(self):
        """브라우저 열기"""
        print("🌐 브라우저 열기...")
        time.sleep(2)  # 서버가 완전히 시작될 때까지 대기
        try:
            webbrowser.open('http://localhost:8000')
        except Exception as e:
            print(f"⚠️  브라우저를 자동으로 열 수 없습니다: {e}")
            print("   수동으로 http://localhost:8000 을 열어주세요.")

    def start_monitoring(self):
        """모니터링 시작"""
        print("\n" + "=" * 60)
        print("🚀 데이터 수집 시작!")
        print("=" * 60)
        print(f"수집 간격: {self.interval}초")
        print(f"총 수집 시간: {self.duration}초 ({self.duration // 60}분)")
        print(f"예상 샘플 수: {self.duration // self.interval}개")
        print()

        # 데이터 수집 시작
        self.data_collector.start_collection()

        # 진행 상황 표시
        start_time = time.time()
        while self.data_collector.is_collecting:
            elapsed = int(time.time() - start_time)
            remaining = max(0, self.duration - elapsed)
            progress = (elapsed / self.duration) * 100

            # 진행 바 표시
            bar_length = 40
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)

            print(f"\r진행: [{bar}] {progress:.1f}% | "
                  f"경과: {elapsed}초 | 남은 시간: {remaining}초 | "
                  f"샘플: {len(self.data_collector.collected_data)}개", end='', flush=True)

            time.sleep(1)

        print("\n\n✅ 데이터 수집 완료!")

    def generate_pdf_report(self):
        """PDF 리포트 생성"""
        print("\n" + "=" * 60)
        print("📄 PDF 리포트 생성 중...")
        print("=" * 60)

        try:
            # 리포트 경로 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.report_path = f"reports/system_monitor_report_{timestamp}.pdf"

            # PDF 생성
            generator = PDFReportGenerator(self.data_collector)
            generator.generate_report(self.report_path)

            print(f"✅ PDF 리포트 생성 완료!")
            print(f"📁 저장 위치: {os.path.abspath(self.report_path)}")

            # 클라이언트에게 완료 알림
            self.ws_server.send_data({
                "type": "completion",
                "report_path": os.path.abspath(self.report_path),
                "message": "모니터링 완료"
            })

        except Exception as e:
            print(f"❌ PDF 생성 실패: {e}")
            import traceback
            traceback.print_exc()

    def show_summary(self):
        """요약 통계 표시"""
        print("\n" + "=" * 60)
        print("📊 모니터링 요약")
        print("=" * 60)

        summary = self.data_collector.get_summary_statistics()

        if summary:
            print(f"\n수집 기간: {summary['collection_start']} ~ {summary['collection_end']}")
            print(f"총 샘플 수: {summary['total_samples']}개")

            print("\n[CPU]")
            cpu = summary['cpu']
            print(f"  평균: {cpu['usage_avg']}% | 최소: {cpu['usage_min']}% | 최대: {cpu['usage_max']}%")
            if cpu['temp_avg']:
                print(f"  온도 평균: {cpu['temp_avg']}°C | 최대: {cpu['temp_max']}°C")

            print("\n[메모리]")
            mem = summary['memory']
            print(f"  평균: {mem['usage_avg']}% | 최소: {mem['usage_min']}% | 최대: {mem['usage_max']}%")

            print("\n[네트워크]")
            net = summary['network']
            print(f"  업로드 평균: {net['upload_avg']} MB/s | 최대: {net['upload_max']} MB/s")
            print(f"  다운로드 평균: {net['download_avg']} MB/s | 최대: {net['download_max']} MB/s")

            if summary['gpu']:
                print("\n[GPU]")
                for gpu in summary['gpu']:
                    print(f"  {gpu['name']}")
                    print(f"    사용률 평균: {gpu['usage_avg']}% | 최대: {gpu['usage_max']}%")
                    if gpu['temp_avg']:
                        print(f"    온도 평균: {gpu['temp_avg']}°C | 최대: {gpu['temp_max']}°C")

    def run(self):
        """애플리케이션 실행"""
        try:
            # 1. 서버 시작
            self.start_servers()

            # 2. 브라우저 열기 (별도 스레드)
            browser_thread = threading.Thread(target=self.open_browser)
            browser_thread.daemon = True
            browser_thread.start()

            # 3. 모니터링 시작
            self.start_monitoring()

            # 4. 요약 표시
            self.show_summary()

            # 5. PDF 리포트 생성
            self.generate_pdf_report()

            # 6. 종료 안내
            print("\n" + "=" * 60)
            print("프로그램이 계속 실행됩니다. 대시보드를 확인하세요.")
            print("종료하려면 Ctrl+C를 누르세요.")
            print("=" * 60)

            # 서버 유지
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n종료 중...")
            self.cleanup()
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            self.cleanup()

    def cleanup(self):
        """정리 작업"""
        print("정리 중...")
        self.data_collector.stop_collection()
        print("✅ 프로그램이 종료되었습니다.")


def main():
    """메인 함수"""
    # 인자 파싱 (간단하게)
    interval = 1  # 1초 간격
    duration = 300  # 5분

    # 사용자 지정 시간 (옵션)
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
            print(f"모니터링 시간: {duration}초로 설정됨")
        except ValueError:
            print("⚠️  잘못된 인자입니다. 기본값(300초) 사용")

    # 애플리케이션 실행
    app = SystemMonitorApp(interval=interval, duration=duration)
    app.run()


if __name__ == "__main__":
    main()
