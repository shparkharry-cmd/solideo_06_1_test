"""
데이터 수집 및 저장 모듈
모니터링 데이터를 수집하고 저장합니다.
"""

import json
import threading
import time
from datetime import datetime
from typing import List, Dict, Any
from backend.monitor import SystemMonitor


class DataCollector:
    """데이터 수집 및 관리 클래스"""

    def __init__(self, interval: int = 1, duration: int = 300):
        """
        Args:
            interval: 데이터 수집 간격 (초)
            duration: 총 수집 시간 (초)
        """
        self.interval = interval
        self.duration = duration
        self.monitor = SystemMonitor()
        self.collected_data: List[Dict[str, Any]] = []
        self.is_collecting = False
        self.collection_thread = None
        self.start_time = None
        self.callbacks = []

    def add_callback(self, callback):
        """데이터 수집 시 호출될 콜백 함수 등록"""
        self.callbacks.append(callback)

    def _notify_callbacks(self, data: Dict[str, Any]):
        """등록된 콜백 함수들에게 데이터 전달"""
        for callback in self.callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"Callback error: {e}")

    def start_collection(self):
        """데이터 수집 시작"""
        if self.is_collecting:
            return False

        self.is_collecting = True
        self.collected_data = []
        self.start_time = datetime.now()

        self.collection_thread = threading.Thread(target=self._collection_loop)
        self.collection_thread.daemon = True
        self.collection_thread.start()

        return True

    def _collection_loop(self):
        """데이터 수집 루프"""
        start_time = time.time()
        end_time = start_time + self.duration

        while self.is_collecting and time.time() < end_time:
            try:
                # 데이터 수집
                data = self.monitor.collect_all_data()
                data['elapsed_seconds'] = int(time.time() - start_time)
                data['remaining_seconds'] = max(0, int(end_time - time.time()))

                # 저장
                self.collected_data.append(data)

                # 콜백 호출
                self._notify_callbacks(data)

                # 다음 수집까지 대기
                time.sleep(self.interval)

            except Exception as e:
                print(f"Collection error: {e}")

        # 수집 종료
        self.is_collecting = False
        self._on_collection_complete()

    def _on_collection_complete(self):
        """수집 완료 시 호출"""
        print(f"Data collection completed. Total samples: {len(self.collected_data)}")

    def stop_collection(self):
        """데이터 수집 중지"""
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)

    def get_latest_data(self) -> Dict[str, Any]:
        """최신 데이터 반환"""
        if self.collected_data:
            return self.collected_data[-1]
        return {}

    def get_all_data(self) -> List[Dict[str, Any]]:
        """모든 수집 데이터 반환"""
        return self.collected_data

    def get_summary_statistics(self) -> Dict[str, Any]:
        """수집된 데이터의 통계 정보"""
        if not self.collected_data:
            return {}

        # CPU 통계
        cpu_usage = [d['cpu']['usage_percent'] for d in self.collected_data]
        cpu_temp = [d['cpu']['temperature'] for d in self.collected_data if d['cpu']['temperature'] is not None]

        # 메모리 통계
        memory_usage = [d['memory']['usage_percent'] for d in self.collected_data]

        # 네트워크 통계
        network_upload = [d['network']['upload_speed_mb'] for d in self.collected_data]
        network_download = [d['network']['download_speed_mb'] for d in self.collected_data]

        # GPU 통계
        gpu_stats = []
        if self.collected_data[0]['gpu']:
            for gpu_idx in range(len(self.collected_data[0]['gpu'])):
                gpu_usage = [d['gpu'][gpu_idx]['usage_percent'] for d in self.collected_data if len(d['gpu']) > gpu_idx]
                gpu_temp = [d['gpu'][gpu_idx]['temperature'] for d in self.collected_data if len(d['gpu']) > gpu_idx and d['gpu'][gpu_idx]['temperature']]

                gpu_stats.append({
                    "name": self.collected_data[0]['gpu'][gpu_idx]['name'],
                    "usage_avg": round(sum(gpu_usage) / len(gpu_usage), 2) if gpu_usage else 0,
                    "usage_max": round(max(gpu_usage), 2) if gpu_usage else 0,
                    "usage_min": round(min(gpu_usage), 2) if gpu_usage else 0,
                    "temp_avg": round(sum(gpu_temp) / len(gpu_temp), 2) if gpu_temp else None,
                    "temp_max": round(max(gpu_temp), 2) if gpu_temp else None,
                })

        # 디스크 통계
        disk_stats = []
        if self.collected_data[0]['disk']:
            for disk_idx in range(len(self.collected_data[0]['disk'])):
                disk_read = [d['disk'][disk_idx]['read_speed_mb'] for d in self.collected_data if len(d['disk']) > disk_idx]
                disk_write = [d['disk'][disk_idx]['write_speed_mb'] for d in self.collected_data if len(d['disk']) > disk_idx]

                disk_stats.append({
                    "device": self.collected_data[0]['disk'][disk_idx]['device'],
                    "mountpoint": self.collected_data[0]['disk'][disk_idx]['mountpoint'],
                    "usage_percent": self.collected_data[-1]['disk'][disk_idx]['usage_percent'],
                    "read_avg": round(sum(disk_read) / len(disk_read), 2) if disk_read else 0,
                    "read_max": round(max(disk_read), 2) if disk_read else 0,
                    "write_avg": round(sum(disk_write) / len(disk_write), 2) if disk_write else 0,
                    "write_max": round(max(disk_write), 2) if disk_write else 0,
                })

        return {
            "collection_start": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else None,
            "collection_end": self.collected_data[-1]['timestamp'] if self.collected_data else None,
            "total_samples": len(self.collected_data),
            "cpu": {
                "usage_avg": round(sum(cpu_usage) / len(cpu_usage), 2),
                "usage_max": round(max(cpu_usage), 2),
                "usage_min": round(min(cpu_usage), 2),
                "temp_avg": round(sum(cpu_temp) / len(cpu_temp), 2) if cpu_temp else None,
                "temp_max": round(max(cpu_temp), 2) if cpu_temp else None,
            },
            "memory": {
                "usage_avg": round(sum(memory_usage) / len(memory_usage), 2),
                "usage_max": round(max(memory_usage), 2),
                "usage_min": round(min(memory_usage), 2),
            },
            "network": {
                "upload_avg": round(sum(network_upload) / len(network_upload), 2),
                "upload_max": round(max(network_upload), 2),
                "download_avg": round(sum(network_download) / len(network_download), 2),
                "download_max": round(max(network_download), 2),
            },
            "gpu": gpu_stats,
            "disk": disk_stats
        }

    def save_to_json(self, filepath: str):
        """수집 데이터를 JSON 파일로 저장"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": self.get_summary_statistics(),
                "data": self.collected_data
            }, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # 테스트 (10초 수집)
    collector = DataCollector(interval=1, duration=10)

    def on_data(data):
        print(f"Collected at {data['timestamp']}: CPU {data['cpu']['usage_percent']}%")

    collector.add_callback(on_data)
    collector.start_collection()

    # 수집 대기
    while collector.is_collecting:
        time.sleep(1)

    print("\nSummary Statistics:")
    print(json.dumps(collector.get_summary_statistics(), indent=2, ensure_ascii=False))
