// 전역 변수
let ws = null;
let charts = {};
let gaugeCharts = {};
let dataHistory = {
    cpu: [],
    memory: [],
    network_upload: [],
    network_download: [],
    temperature: [],
    timestamps: []
};

const MAX_DATA_POINTS = 300; // 5분 (300초)
let startTime = null;

// WebSocket 연결
function connectWebSocket() {
    const wsUrl = `ws://${window.location.hostname}:8765`;
    console.log('Connecting to WebSocket:', wsUrl);

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionStatus(true);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('Received data:', data);
            handleDataUpdate(data);
        } catch (error) {
            console.error('Error parsing data:', error);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus(false);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateConnectionStatus(false);
        // 재연결 시도
        setTimeout(connectWebSocket, 3000);
    };
}

// 연결 상태 업데이트
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connection-status');
    if (connected) {
        statusEl.textContent = '연결됨';
        statusEl.className = 'status-value connected';
    } else {
        statusEl.textContent = '연결 끊김';
        statusEl.className = 'status-value disconnected';
    }
}

// 데이터 업데이트 처리
function handleDataUpdate(data) {
    if (!startTime) {
        startTime = Date.now();
    }

    // 타이머 업데이트
    const elapsed = data.elapsed_seconds || 0;
    const remaining = data.remaining_seconds || 0;
    updateTimer(elapsed, remaining);

    // 상태 업데이트
    document.getElementById('collection-status').textContent = '수집 중';
    document.getElementById('sample-count').textContent = dataHistory.timestamps.length;

    // 데이터 히스토리 저장
    const timestamp = dataHistory.timestamps.length;
    dataHistory.timestamps.push(timestamp);
    dataHistory.cpu.push(data.cpu.usage_percent);
    dataHistory.memory.push(data.memory.usage_percent);
    dataHistory.network_upload.push(data.network.upload_speed_mb);
    dataHistory.network_download.push(data.network.download_speed_mb);

    if (data.cpu.temperature) {
        dataHistory.temperature.push(data.cpu.temperature);
        showTemperatureChart();
    }

    // 데이터 포인트 제한
    if (dataHistory.timestamps.length > MAX_DATA_POINTS) {
        dataHistory.timestamps.shift();
        dataHistory.cpu.shift();
        dataHistory.memory.shift();
        dataHistory.network_upload.shift();
        dataHistory.network_download.shift();
        if (dataHistory.temperature.length > 0) {
            dataHistory.temperature.shift();
        }
    }

    // UI 업데이트
    updateGauges(data);
    updateCharts();
    updateProcessTables(data.processes);
    updateInfoDisplays(data);

    // GPU 표시
    if (data.gpu && data.gpu.length > 0) {
        document.getElementById('gpu-card').style.display = 'block';
        updateGPUGauge(data.gpu[0]);
    }

    // 수집 완료 확인
    if (remaining === 0) {
        onCollectionComplete();
    }
}

// 타이머 업데이트
function updateTimer(elapsed, remaining) {
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    const timerText = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    document.getElementById('timer').textContent = timerText;
}

// 게이지 차트 초기화
function initGauges() {
    const gaugeConfig = (label, color) => ({
        type: 'doughnut',
        data: {
            datasets: [{
                data: [0, 100],
                backgroundColor: [color, '#e0e0e0'],
                borderWidth: 0
            }]
        },
        options: {
            cutout: '75%',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            }
        }
    });

    gaugeCharts.cpu = new Chart(
        document.getElementById('cpu-gauge'),
        gaugeConfig('CPU', '#3498db')
    );

    gaugeCharts.memory = new Chart(
        document.getElementById('memory-gauge'),
        gaugeConfig('Memory', '#e74c3c')
    );

    gaugeCharts.disk = new Chart(
        document.getElementById('disk-gauge'),
        gaugeConfig('Disk', '#f39c12')
    );

    gaugeCharts.gpu = new Chart(
        document.getElementById('gpu-gauge'),
        gaugeConfig('GPU', '#9b59b6')
    );
}

// 게이지 업데이트
function updateGauges(data) {
    updateGauge(gaugeCharts.cpu, data.cpu.usage_percent, 'cpu-current');
    updateGauge(gaugeCharts.memory, data.memory.usage_percent, 'memory-current');

    if (data.disk && data.disk.length > 0) {
        updateGauge(gaugeCharts.disk, data.disk[0].usage_percent, 'disk-current');
    }
}

// 개별 게이지 업데이트
function updateGauge(chart, value, elementId) {
    const color = getColorForValue(value);
    chart.data.datasets[0].data = [value, 100 - value];
    chart.data.datasets[0].backgroundColor = [color, '#e0e0e0'];
    chart.update('none');

    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = `${value.toFixed(1)}%`;
        element.className = `info-value ${getClassForValue(value)}`;
    }
}

// GPU 게이지 업데이트
function updateGPUGauge(gpu) {
    updateGauge(gaugeCharts.gpu, gpu.usage_percent, 'gpu-current');

    if (gpu.temperature) {
        document.getElementById('gpu-temp').textContent = `${gpu.temperature.toFixed(1)}°C`;
    }
}

// 값에 따른 색상 결정
function getColorForValue(value) {
    if (value < 60) return '#28a745'; // 녹색
    if (value < 80) return '#ffc107'; // 노란색
    return '#dc3545'; // 빨간색
}

// 값에 따른 클래스 결정
function getClassForValue(value) {
    if (value < 60) return 'normal';
    if (value < 80) return 'warning';
    return 'danger';
}

// 라인 차트 초기화
function initCharts() {
    const chartConfig = (label, borderColor, backgroundColor) => ({
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: label,
                data: [],
                borderColor: borderColor,
                backgroundColor: backgroundColor,
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    display: true,
                    title: { display: true, text: '시간 (초)' }
                },
                y: {
                    display: true,
                    title: { display: true, text: '사용률 (%)' },
                    min: 0,
                    max: 100
                }
            },
            animation: {
                duration: 0
            }
        }
    });

    charts.cpu = new Chart(
        document.getElementById('cpu-chart'),
        chartConfig('CPU 사용률', '#3498db', 'rgba(52, 152, 219, 0.2)')
    );

    charts.memory = new Chart(
        document.getElementById('memory-chart'),
        chartConfig('메모리 사용률', '#e74c3c', 'rgba(231, 76, 60, 0.2)')
    );

    // 네트워크 차트
    charts.network = new Chart(
        document.getElementById('network-chart'),
        {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: '업로드',
                        data: [],
                        borderColor: '#2ecc71',
                        backgroundColor: 'rgba(46, 204, 113, 0.2)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: '다운로드',
                        data: [],
                        borderColor: '#9b59b6',
                        backgroundColor: 'rgba(155, 89, 182, 0.2)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2.5,
                plugins: {
                    legend: { display: true, position: 'top' }
                },
                scales: {
                    x: {
                        display: true,
                        title: { display: true, text: '시간 (초)' }
                    },
                    y: {
                        display: true,
                        title: { display: true, text: '속도 (MB/s)' },
                        min: 0
                    }
                },
                animation: {
                    duration: 0
                }
            }
        }
    );
}

// 차트 업데이트
function updateCharts() {
    // CPU 차트
    charts.cpu.data.labels = dataHistory.timestamps;
    charts.cpu.data.datasets[0].data = dataHistory.cpu;
    charts.cpu.update('none');

    // 메모리 차트
    charts.memory.data.labels = dataHistory.timestamps;
    charts.memory.data.datasets[0].data = dataHistory.memory;
    charts.memory.update('none');

    // 네트워크 차트
    charts.network.data.labels = dataHistory.timestamps;
    charts.network.data.datasets[0].data = dataHistory.network_upload;
    charts.network.data.datasets[1].data = dataHistory.network_download;
    charts.network.update('none');

    // 온도 차트
    if (charts.temperature && dataHistory.temperature.length > 0) {
        charts.temperature.data.labels = dataHistory.timestamps.slice(-dataHistory.temperature.length);
        charts.temperature.data.datasets[0].data = dataHistory.temperature;
        charts.temperature.update('none');
    }
}

// 온도 차트 표시
function showTemperatureChart() {
    const chartCard = document.getElementById('temp-chart-card');
    if (chartCard.style.display === 'none') {
        chartCard.style.display = 'block';
        charts.temperature = new Chart(
            document.getElementById('temp-chart'),
            {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'CPU 온도',
                        data: [],
                        borderColor: '#e67e22',
                        backgroundColor: 'rgba(230, 126, 34, 0.2)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    aspectRatio: 2.5,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            display: true,
                            title: { display: true, text: '시간 (초)' }
                        },
                        y: {
                            display: true,
                            title: { display: true, text: '온도 (°C)' },
                            min: 0
                        }
                    },
                    animation: {
                        duration: 0
                    }
                }
            }
        );
    }
}

// 정보 표시 업데이트
function updateInfoDisplays(data) {
    // CPU 온도
    if (data.cpu.temperature) {
        document.getElementById('cpu-temp').textContent = `${data.cpu.temperature.toFixed(1)}°C`;
    }

    // 메모리 사용량
    document.getElementById('memory-used').textContent =
        `${data.memory.used_gb.toFixed(1)} GB / ${data.memory.total_gb.toFixed(1)} GB`;

    // 디스크 용량
    if (data.disk && data.disk.length > 0) {
        document.getElementById('disk-space').textContent =
            `${data.disk[0].used_gb.toFixed(1)} GB / ${data.disk[0].total_gb.toFixed(1)} GB`;
    }

    // 네트워크 속도
    document.getElementById('network-upload').textContent =
        `${data.network.upload_speed_mb.toFixed(2)} MB/s`;
    document.getElementById('network-download').textContent =
        `${data.network.download_speed_mb.toFixed(2)} MB/s`;
}

// 프로세스 테이블 업데이트
function updateProcessTables(processes) {
    if (!processes) return;

    // CPU 프로세스
    const cpuTable = document.getElementById('cpu-process-table').querySelector('tbody');
    cpuTable.innerHTML = '';
    processes.top_cpu.forEach((proc, idx) => {
        const row = cpuTable.insertRow();
        row.innerHTML = `
            <td>${idx + 1}</td>
            <td>${proc.name}</td>
            <td>${proc.pid}</td>
            <td class="${getClassForValue(proc.cpu_percent)}">${proc.cpu_percent.toFixed(1)}%</td>
            <td>${proc.memory_mb.toFixed(1)}</td>
        `;
    });

    // 메모리 프로세스
    const memTable = document.getElementById('memory-process-table').querySelector('tbody');
    memTable.innerHTML = '';
    processes.top_memory.forEach((proc, idx) => {
        const row = memTable.insertRow();
        row.innerHTML = `
            <td>${idx + 1}</td>
            <td>${proc.name}</td>
            <td>${proc.pid}</td>
            <td class="${getClassForValue(proc.memory_percent)}">${proc.memory_percent.toFixed(1)}%</td>
            <td>${proc.memory_mb.toFixed(1)}</td>
        `;
    });
}

// 수집 완료 처리
function onCollectionComplete() {
    document.getElementById('collection-status').textContent = '완료';
    document.getElementById('completion-message').style.display = 'block';

    // 스크롤
    document.getElementById('completion-message').scrollIntoView({ behavior: 'smooth' });
}

// 페이지 로드 시 초기화
window.addEventListener('load', () => {
    console.log('Initializing dashboard...');
    initGauges();
    initCharts();
    connectWebSocket();
});
