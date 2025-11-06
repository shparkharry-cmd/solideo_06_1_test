"""
시스템 리소스 모니터링 모듈
CPU, GPU, 메모리, 디스크, 네트워크, 프로세스 정보를 수집합니다.
"""

import psutil
import platform
from datetime import datetime
from typing import Dict, List, Any

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False


class SystemMonitor:
    """시스템 리소스 모니터링 클래스"""

    def __init__(self):
        self.net_io_start = psutil.net_io_counters()
        self.disk_io_start = {}
        for disk in psutil.disk_partitions():
            try:
                self.disk_io_start[disk.device] = psutil.disk_io_counters(perdisk=True)
            except:
                pass
        self.last_net_io = self.net_io_start
        self.last_disk_io = self.disk_io_start.copy()

    def get_cpu_info(self) -> Dict[str, Any]:
        """CPU 정보 수집"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        cpu_freq = psutil.cpu_freq()

        # CPU 온도 (Linux의 경우)
        temperature = None
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    # coretemp 또는 k10temp (AMD) 찾기
                    for name, entries in temps.items():
                        if name in ['coretemp', 'k10temp', 'cpu_thermal']:
                            if entries:
                                temperature = entries[0].current
                                break
        except:
            pass

        return {
            "usage_percent": round(cpu_percent, 2),
            "core_usage": [round(x, 2) for x in cpu_per_core],
            "core_count": psutil.cpu_count(logical=False),
            "thread_count": psutil.cpu_count(logical=True),
            "frequency_current": round(cpu_freq.current, 2) if cpu_freq else None,
            "frequency_max": round(cpu_freq.max, 2) if cpu_freq else None,
            "temperature": round(temperature, 2) if temperature else None
        }

    def get_gpu_info(self) -> List[Dict[str, Any]]:
        """GPU 정보 수집"""
        if not GPU_AVAILABLE:
            return []

        try:
            gpus = GPUtil.getGPUs()
            gpu_list = []

            for gpu in gpus:
                gpu_list.append({
                    "id": gpu.id,
                    "name": gpu.name,
                    "usage_percent": round(gpu.load * 100, 2),
                    "memory_used": round(gpu.memoryUsed, 2),
                    "memory_total": round(gpu.memoryTotal, 2),
                    "memory_percent": round((gpu.memoryUsed / gpu.memoryTotal) * 100, 2) if gpu.memoryTotal > 0 else 0,
                    "temperature": round(gpu.temperature, 2) if gpu.temperature else None
                })

            return gpu_list
        except Exception as e:
            return []

    def get_memory_info(self) -> Dict[str, Any]:
        """메모리 정보 수집"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "usage_percent": round(mem.percent, 2),
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2),
            "swap_percent": round(swap.percent, 2)
        }

    def get_disk_info(self) -> List[Dict[str, Any]]:
        """디스크 정보 수집"""
        disk_list = []

        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)

                # 읽기/쓰기 속도 계산
                read_speed = 0
                write_speed = 0

                try:
                    disk_io = psutil.disk_io_counters(perdisk=True)
                    device_name = partition.device.replace('/dev/', '')

                    if device_name in disk_io:
                        current_io = disk_io[device_name]
                        if partition.device in self.last_disk_io:
                            last_io = self.last_disk_io[partition.device]
                            read_speed = (current_io.read_bytes - last_io.read_bytes) / (1024**2)  # MB/s
                            write_speed = (current_io.write_bytes - last_io.write_bytes) / (1024**2)  # MB/s
                        self.last_disk_io[partition.device] = current_io
                except:
                    pass

                disk_list.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "usage_percent": round(usage.percent, 2),
                    "read_speed_mb": round(read_speed, 2),
                    "write_speed_mb": round(write_speed, 2)
                })
            except PermissionError:
                continue
            except Exception as e:
                continue

        return disk_list

    def get_network_info(self) -> Dict[str, Any]:
        """네트워크 정보 수집"""
        current_net_io = psutil.net_io_counters()

        # 속도 계산 (MB/s)
        upload_speed = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / (1024**2)
        download_speed = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / (1024**2)

        self.last_net_io = current_net_io

        return {
            "upload_speed_mb": round(upload_speed, 2),
            "download_speed_mb": round(download_speed, 2),
            "total_sent_gb": round(current_net_io.bytes_sent / (1024**3), 2),
            "total_recv_gb": round(current_net_io.bytes_recv / (1024**3), 2),
            "packets_sent": current_net_io.packets_sent,
            "packets_recv": current_net_io.packets_recv
        }

    def get_top_processes(self, count: int = 5) -> List[Dict[str, Any]]:
        """CPU/메모리 사용 상위 프로세스"""
        processes = []

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
            try:
                pinfo = proc.info
                processes.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "cpu_percent": round(pinfo['cpu_percent'] or 0, 2),
                    "memory_percent": round(pinfo['memory_percent'] or 0, 2),
                    "memory_mb": round(pinfo['memory_info'].rss / (1024**2), 2) if pinfo['memory_info'] else 0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # CPU 사용률로 정렬
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        top_cpu = processes[:count]

        # 메모리 사용률로 정렬
        processes.sort(key=lambda x: x['memory_percent'], reverse=True)
        top_memory = processes[:count]

        return {
            "top_cpu": top_cpu,
            "top_memory": top_memory
        }

    def get_system_info(self) -> Dict[str, Any]:
        """시스템 기본 정보"""
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        }

    def collect_all_data(self) -> Dict[str, Any]:
        """모든 시스템 데이터 수집"""
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cpu": self.get_cpu_info(),
            "gpu": self.get_gpu_info(),
            "memory": self.get_memory_info(),
            "disk": self.get_disk_info(),
            "network": self.get_network_info(),
            "processes": self.get_top_processes(),
            "system_info": self.get_system_info()
        }


if __name__ == "__main__":
    # 테스트
    import json
    monitor = SystemMonitor()
    data = monitor.collect_all_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
