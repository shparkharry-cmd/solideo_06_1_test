#!/usr/bin/env python3
"""
빠른 테스트를 위한 스크립트 (10초 모니터링)
"""

import sys
sys.path.insert(0, '.')

from backend.monitor import SystemMonitor
from backend.data_collector import DataCollector

print("=" * 60)
print("빠른 테스트 시작 (10초 모니터링)")
print("=" * 60)

# 데이터 수집기 생성 (10초)
collector = DataCollector(interval=1, duration=10)

def on_data(data):
    print(f"✓ {data['timestamp']}: CPU {data['cpu']['usage_percent']}% | "
          f"Memory {data['memory']['usage_percent']}%")

collector.add_callback(on_data)
collector.start_collection()

# 수집 대기
import time
while collector.is_collecting:
    time.sleep(1)

print("\n" + "=" * 60)
print("요약 통계:")
print("=" * 60)

summary = collector.get_summary_statistics()
if summary:
    print(f"샘플 수: {summary['total_samples']}")
    print(f"CPU 평균: {summary['cpu']['usage_avg']}%")
    print(f"메모리 평균: {summary['memory']['usage_avg']}%")

print("\n✅ 테스트 완료!")
