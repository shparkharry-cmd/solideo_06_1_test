"""
PDF 리포트 생성 모듈
시스템 모니터링 데이터를 PDF 리포트로 생성합니다.
"""

import io
import os
from datetime import datetime
from typing import List, Dict, Any

import matplotlib
matplotlib.use('Agg')  # GUI 없이 사용
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.pdfgen import canvas


class PDFReportGenerator:
    """PDF 리포트 생성 클래스"""

    def __init__(self, data_collector):
        self.collector = data_collector
        self.data = data_collector.get_all_data()
        self.summary = data_collector.get_summary_statistics()

    def generate_report(self, output_path: str):
        """PDF 리포트 생성"""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        # 스타일 설정
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=1  # 중앙 정렬
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12
        )

        # PDF 컨텐츠
        story = []

        # 표지
        story.extend(self._create_cover_page(title_style, styles))

        # 시스템 정보
        story.append(Paragraph("시스템 정보", heading_style))
        story.append(self._create_system_info_table())
        story.append(Spacer(1, 0.3*inch))

        # 요약 통계
        story.append(Paragraph("모니터링 요약", heading_style))
        story.append(self._create_summary_table())
        story.append(Spacer(1, 0.3*inch))

        # 페이지 나누기
        story.append(PageBreak())

        # 그래프 추가
        story.append(Paragraph("시간별 리소스 사용 추이", heading_style))

        # CPU 그래프
        cpu_chart = self._create_cpu_chart()
        if cpu_chart:
            story.append(Image(cpu_chart, width=6.5*inch, height=2.5*inch))
            story.append(Spacer(1, 0.2*inch))

        # 메모리 그래프
        memory_chart = self._create_memory_chart()
        if memory_chart:
            story.append(Image(memory_chart, width=6.5*inch, height=2.5*inch))
            story.append(Spacer(1, 0.2*inch))

        # 페이지 나누기
        story.append(PageBreak())

        # 네트워크 그래프
        story.append(Paragraph("네트워크 사용 추이", heading_style))
        network_chart = self._create_network_chart()
        if network_chart:
            story.append(Image(network_chart, width=6.5*inch, height=2.5*inch))
            story.append(Spacer(1, 0.2*inch))

        # 온도 그래프 (있는 경우)
        if self.summary.get('cpu', {}).get('temp_avg'):
            story.append(Paragraph("온도 추이", heading_style))
            temp_chart = self._create_temperature_chart()
            if temp_chart:
                story.append(Image(temp_chart, width=6.5*inch, height=2.5*inch))
                story.append(Spacer(1, 0.2*inch))

        # 페이지 나누기
        story.append(PageBreak())

        # 프로세스 테이블
        story.append(Paragraph("상위 프로세스 (최종 측정 시점)", heading_style))
        story.append(self._create_process_table())
        story.append(Spacer(1, 0.3*inch))

        # 분석 및 권장사항
        story.append(Paragraph("분석 및 권장사항", heading_style))
        story.append(self._create_analysis())

        # PDF 빌드
        doc.build(story)
        print(f"PDF report generated: {output_path}")

    def _create_cover_page(self, title_style, styles):
        """표지 페이지"""
        elements = []

        elements.append(Spacer(1, 1.5*inch))
        elements.append(Paragraph("시스템 리소스 모니터링 리포트", title_style))
        elements.append(Spacer(1, 0.5*inch))

        # 모니터링 정보
        info_style = styles['Normal']
        info_style.fontSize = 12
        info_style.alignment = 1  # 중앙 정렬

        if self.summary:
            elements.append(Paragraph(f"<b>모니터링 기간:</b> {self.summary.get('collection_start', 'N/A')} ~ {self.summary.get('collection_end', 'N/A')}", info_style))
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(f"<b>총 샘플 수:</b> {self.summary.get('total_samples', 0)}", info_style))
            elements.append(Spacer(1, 0.1*inch))

        elements.append(Paragraph(f"<b>리포트 생성:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", info_style))

        elements.append(PageBreak())
        return elements

    def _create_system_info_table(self):
        """시스템 정보 테이블"""
        if not self.data:
            return Paragraph("데이터 없음", getSampleStyleSheet()['Normal'])

        sys_info = self.data[0].get('system_info', {})

        data = [
            ['항목', '정보'],
            ['운영체제', f"{sys_info.get('platform', 'N/A')} {sys_info.get('platform_release', '')}"],
            ['아키텍처', sys_info.get('architecture', 'N/A')],
            ['프로세서', sys_info.get('processor', 'N/A')],
            ['호스트명', sys_info.get('hostname', 'N/A')],
            ['부팅 시간', sys_info.get('boot_time', 'N/A')],
        ]

        table = Table(data, colWidths=[2*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        return table

    def _create_summary_table(self):
        """요약 통계 테이블"""
        if not self.summary:
            return Paragraph("데이터 없음", getSampleStyleSheet()['Normal'])

        cpu = self.summary.get('cpu', {})
        memory = self.summary.get('memory', {})
        network = self.summary.get('network', {})

        data = [
            ['리소스', '평균', '최소', '최대'],
            ['CPU 사용률 (%)', f"{cpu.get('usage_avg', 0)}", f"{cpu.get('usage_min', 0)}", f"{cpu.get('usage_max', 0)}"],
            ['메모리 사용률 (%)', f"{memory.get('usage_avg', 0)}", f"{memory.get('usage_min', 0)}", f"{memory.get('usage_max', 0)}"],
            ['업로드 속도 (MB/s)', f"{network.get('upload_avg', 0)}", '-', f"{network.get('upload_max', 0)}"],
            ['다운로드 속도 (MB/s)', f"{network.get('download_avg', 0)}", '-', f"{network.get('download_max', 0)}"],
        ]

        if cpu.get('temp_avg'):
            data.append(['CPU 온도 (°C)', f"{cpu.get('temp_avg', 0)}", '-', f"{cpu.get('temp_max', 0)}"])

        table = Table(data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        return table

    def _create_cpu_chart(self):
        """CPU 사용률 차트"""
        if not self.data:
            return None

        timestamps = [i for i in range(len(self.data))]
        cpu_usage = [d['cpu']['usage_percent'] for d in self.data]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(timestamps, cpu_usage, linewidth=2, color='#3498db')
        ax.fill_between(timestamps, cpu_usage, alpha=0.3, color='#3498db')
        ax.set_xlabel('시간 (초)', fontsize=10)
        ax.set_ylabel('CPU 사용률 (%)', fontsize=10)
        ax.set_title('CPU 사용률 추이', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)

        # 메모리에 이미지 저장
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()

        return buf

    def _create_memory_chart(self):
        """메모리 사용률 차트"""
        if not self.data:
            return None

        timestamps = [i for i in range(len(self.data))]
        memory_usage = [d['memory']['usage_percent'] for d in self.data]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(timestamps, memory_usage, linewidth=2, color='#e74c3c')
        ax.fill_between(timestamps, memory_usage, alpha=0.3, color='#e74c3c')
        ax.set_xlabel('시간 (초)', fontsize=10)
        ax.set_ylabel('메모리 사용률 (%)', fontsize=10)
        ax.set_title('메모리 사용률 추이', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()

        return buf

    def _create_network_chart(self):
        """네트워크 사용량 차트"""
        if not self.data:
            return None

        timestamps = [i for i in range(len(self.data))]
        upload = [d['network']['upload_speed_mb'] for d in self.data]
        download = [d['network']['download_speed_mb'] for d in self.data]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(timestamps, upload, linewidth=2, color='#2ecc71', label='업로드')
        ax.plot(timestamps, download, linewidth=2, color='#9b59b6', label='다운로드')
        ax.fill_between(timestamps, upload, alpha=0.3, color='#2ecc71')
        ax.fill_between(timestamps, download, alpha=0.3, color='#9b59b6')
        ax.set_xlabel('시간 (초)', fontsize=10)
        ax.set_ylabel('속도 (MB/s)', fontsize=10)
        ax.set_title('네트워크 속도 추이', fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()

        return buf

    def _create_temperature_chart(self):
        """온도 차트"""
        if not self.data:
            return None

        timestamps = [i for i in range(len(self.data))]
        cpu_temps = [d['cpu']['temperature'] for d in self.data if d['cpu']['temperature'] is not None]

        if not cpu_temps:
            return None

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(timestamps[:len(cpu_temps)], cpu_temps, linewidth=2, color='#e67e22')
        ax.fill_between(timestamps[:len(cpu_temps)], cpu_temps, alpha=0.3, color='#e67e22')
        ax.set_xlabel('시간 (초)', fontsize=10)
        ax.set_ylabel('온도 (°C)', fontsize=10)
        ax.set_title('CPU 온도 추이', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()

        return buf

    def _create_process_table(self):
        """프로세스 테이블"""
        if not self.data:
            return Paragraph("데이터 없음", getSampleStyleSheet()['Normal'])

        processes = self.data[-1].get('processes', {})
        top_cpu = processes.get('top_cpu', [])[:5]

        data = [['순위', '프로세스명', 'PID', 'CPU (%)', '메모리 (%)', '메모리 (MB)']]

        for idx, proc in enumerate(top_cpu, 1):
            data.append([
                str(idx),
                proc['name'][:30],
                str(proc['pid']),
                f"{proc['cpu_percent']}",
                f"{proc['memory_percent']}",
                f"{proc['memory_mb']}"
            ])

        table = Table(data, colWidths=[0.5*inch, 2.5*inch, 0.8*inch, 0.9*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))

        return table

    def _create_analysis(self):
        """분석 및 권장사항"""
        if not self.summary:
            return Paragraph("데이터 없음", getSampleStyleSheet()['Normal'])

        analysis_text = []

        cpu = self.summary.get('cpu', {})
        memory = self.summary.get('memory', {})

        analysis_text.append("<b>리소스 사용 분석:</b><br/><br/>")

        # CPU 분석
        cpu_avg = cpu.get('usage_avg', 0)
        if cpu_avg > 80:
            analysis_text.append("• <b>CPU:</b> 높은 사용률이 감지되었습니다 (평균 {:.1f}%). CPU 집약적인 프로세스를 확인하고 최적화가 필요합니다.<br/>".format(cpu_avg))
        elif cpu_avg > 60:
            analysis_text.append("• <b>CPU:</b> 보통 수준의 사용률입니다 (평균 {:.1f}%). 모니터링을 계속하시기 바랍니다.<br/>".format(cpu_avg))
        else:
            analysis_text.append("• <b>CPU:</b> 정상 수준의 사용률입니다 (평균 {:.1f}%).<br/>".format(cpu_avg))

        # 메모리 분석
        mem_avg = memory.get('usage_avg', 0)
        if mem_avg > 80:
            analysis_text.append("• <b>메모리:</b> 높은 메모리 사용률이 감지되었습니다 (평균 {:.1f}%). 메모리 누수 확인 및 불필요한 프로세스 종료를 권장합니다.<br/>".format(mem_avg))
        elif mem_avg > 60:
            analysis_text.append("• <b>메모리:</b> 보통 수준의 메모리 사용입니다 (평균 {:.1f}%).<br/>".format(mem_avg))
        else:
            analysis_text.append("• <b>메모리:</b> 정상 수준의 메모리 사용입니다 (평균 {:.1f}%).<br/>".format(mem_avg))

        # 온도 분석
        if cpu.get('temp_avg'):
            temp_avg = cpu.get('temp_avg', 0)
            if temp_avg > 80:
                analysis_text.append("• <b>온도:</b> 높은 온도가 감지되었습니다 (평균 {:.1f}°C). 냉각 시스템을 점검하시기 바랍니다.<br/>".format(temp_avg))
            elif temp_avg > 70:
                analysis_text.append("• <b>온도:</b> 주의가 필요한 온도입니다 (평균 {:.1f}°C).<br/>".format(temp_avg))
            else:
                analysis_text.append("• <b>온도:</b> 정상 온도 범위입니다 (평균 {:.1f}°C).<br/>".format(temp_avg))

        analysis_text.append("<br/><b>권장사항:</b><br/><br/>")
        analysis_text.append("• 주기적인 시스템 모니터링을 통해 리소스 사용 패턴을 파악하세요.<br/>")
        analysis_text.append("• 높은 리소스 사용이 지속되는 경우 하드웨어 업그레이드를 고려하세요.<br/>")
        analysis_text.append("• 백그라운드에서 실행되는 불필요한 프로세스를 정리하세요.<br/>")

        return Paragraph(''.join(analysis_text), getSampleStyleSheet()['Normal'])


if __name__ == "__main__":
    # 테스트용 코드는 main.py에서 실행
    pass
