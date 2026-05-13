"""
折线图生成模块

使用matplotlib生成紫外线指数趋势图
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import io
import os
import logging

from .weather import WeatherData
from .config_loader import get_config

logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


class ChartGenerator:
    """图表生成器"""

    # UV等级颜色映射
    UV_COLORS = {
        (0, 2): "#4CAF50",      # 绿色 - 低
        (3, 5): "#FFEB3B",      # 黄色 - 中等
        (6, 7): "#FF9800",      # 橙色 - 高
        (8, 10): "#F44336",     # 红色 - 很高
        (11, 15): "#9C27B0",    # 紫色 - 极高
    }

    def __init__(self):
        self.config = get_config()

    def generate_uv_chart(
        self,
        weather_data: WeatherData,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        生成紫外线指数趋势图
        """
        # 生成0-24小时的UV数据
        times = list(range(25))
        uv_values = []
        temps = []

        hourly_data = {h.get("time", ""): h for h in weather_data.hourly_uv}

        for hour in range(25):
            time_key = f"{hour:02d}:00"
            if time_key in hourly_data:
                uv_values.append(hourly_data[time_key].get("uv", 0))
                temps.append(hourly_data[time_key].get("temp", 25))
            else:
                uv = self._estimate_uv_for_hour(hour, weather_data.max_uv, weather_data.weather)
                uv_values.append(uv)
                temps.append(weather_data.temp_min + (weather_data.temp_max - weather_data.temp_min) * 0.5)

        # 创建图表（增加高度给顶部信息留空间）
        fig, ax1 = plt.subplots(figsize=(12, 6))

        # 绘制UV曲线
        ax1.plot(times, uv_values, '#FF6B6B', linewidth=3, label='UV指数')
        ax1.scatter(times, uv_values, c='#FF6B6B', s=35, zorder=5)

        # 曲线下方填充渐变色（根据UV值）
        for i in range(1, len(times)):
            uv = uv_values[i]
            if uv >= 8:
                color = '#E53935'  # 很高 - 红色
            elif uv >= 6:
                color = '#FF9800'  # 高 - 橙色
            elif uv >= 3:
                color = '#FFCA28'  # 中等 - 黄色
            else:
                color = '#66BB6A'  # 低 - 绿色
            ax1.fill_between([times[i-1], times[i]], 0, [uv_values[i-1], uv_values[i]], alpha=0.4, color=color)

        # 绘制气温曲线
        ax2 = ax1.twinx()
        ax2.plot(times, temps, '#2196F3', linewidth=2, linestyle='--', alpha=0.6, label='气温')
        ax2.set_ylabel('气温 (°C)', color='#2196F3', fontsize=12)
        ax2.tick_params(axis='y', labelcolor='#2196F3', labelsize=11)
        ax2.set_ylim(min(temps) - 5, max(temps) + 5)

        # 设置标题（顶部）
        ax1.set_title(
            f"{weather_data.city} {weather_data.date.strftime('%Y-%m-%d')} 紫外线指数",
            fontsize=16, fontweight='bold', pad=50
        )

        # 天气信息放在标题下方
        info_text = f"天气: {weather_data.weather}  |  最高UV: {weather_data.max_uv}  |  高峰时段: {weather_data.peak_hours}"
        fig.text(0.5, 0.91, info_text, fontsize=12, ha='center', alpha=0.8)

        ax1.set_xlabel("时间", fontsize=12)
        ax1.set_ylabel("紫外线指数 (UV)", fontsize=12, color='#FF6B6B')
        ax1.tick_params(axis='y', labelcolor='#FF6B6B', labelsize=11)

        # X轴设置
        ax1.set_xlim(0, 24)
        ax1.set_xticks([0, 6, 9, 12, 15, 18, 24])
        ax1.set_xticklabels(['0:00', '6:00', '9:00', '12:00', '15:00', '18:00', '24:00'], fontsize=11)

        # Y轴设置
        max_uv = max(uv_values) if uv_values else 10
        ax1.set_ylim(0, max(max_uv + 2, 10))
        ax1.tick_params(axis='x', labelsize=11)

        # 添加UV等级参考线
        ax1.axhline(y=3, color='#FFCA28', linestyle=':', alpha=0.6, linewidth=1.5)
        ax1.axhline(y=6, color='#FF9800', linestyle=':', alpha=0.6, linewidth=1.5)
        ax1.axhline(y=8, color='#E53935', linestyle=':', alpha=0.6, linewidth=1.5)

        # 等级标签放在Y轴右侧（图表内部左侧）
        ax1.text(0.8, 1.5, '低', fontsize=11, color='#66BB6A', va='center', fontweight='bold')
        ax1.text(0.8, 4.5, '中等', fontsize=11, color='#FFCA28', va='center', fontweight='bold')
        ax1.text(0.8, 7, '高', fontsize=11, color='#FF9800', va='center', fontweight='bold')
        ax1.text(0.8, 9, '很高', fontsize=11, color='#E53935', va='center', fontweight='bold')

        # 添加图例
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='#FF6B6B', linewidth=3, label='UV指数'),
            Line2D([0], [0], color='#2196F3', linewidth=2, linestyle='--', label='气温'),
        ]
        ax1.legend(handles=legend_elements, loc='upper right', fontsize=11)

        plt.tight_layout()
        plt.subplots_adjust(top=0.85)

        if output_path is None:
            output_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data",
                f"uv_chart_{weather_data.date.strftime('%Y%m%d')}.png",
            )

        try:
            fig.savefig(output_path, dpi=120, bbox_inches='tight', facecolor='white')
            logger.info(f"图表已保存: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"保存图表失败: {e}")
            return None
        finally:
            plt.close(fig)

    def _estimate_uv_for_hour(self, hour: int, max_uv: float, weather: str) -> float:
        """根据小时估算UV值"""
        import math
        if hour < 6 or hour > 18:
            return 0.3
        normalized = math.sin((hour - 6) * math.pi / 12)
        uv = max_uv * normalized
        if "雨" in weather:
            uv *= 0.3
        elif "阴" in weather or "云" in weather:
            uv *= 0.6
        return round(max(0.3, uv), 1)

    def _plot_uv_curve(self, ax, times: List[int], uv_values: List[float]):
        """绘制UV曲线（带颜色渐变效果）"""
        # 绘制主线
        ax.plot(times, uv_values, 'r-', linewidth=2.5, label='UV指数')

        # 添加数据点
        ax.scatter(times, uv_values, c='red', s=30, zorder=5)

        # 根据UV值添加颜色区域
        for i, (t, uv) in enumerate(zip(times, uv_values)):
            color = self._get_uv_color(uv)
            if i > 0:
                ax.fill_between(
                    [times[i-1], t],
                    [uv_values[i-1], uv],
                    alpha=0.3,
                    color=color,
                )

    def _get_uv_color(self, uv: float) -> str:
        """获取UV对应的颜色"""
        for (low, high), color in self.UV_COLORS.items():
            if low <= uv <= high:
                return color
        return "#F44336"  # 默认红色

    def _add_uv_level_zones(self, ax, max_y: float):
        """添加UV等级区域标注"""
        zones = [
            (0, 2, "#4CAF50", "低"),
            (3, 5, "#FFEB3B", "中等"),
            (6, 7, "#FF9800", "高"),
            (8, 10, "#F44336", "很高"),
            (11, max_y, "#9C27B0", "极高"),
        ]

        for low, high, color, label in zones:
            ax.axhspan(low, high, alpha=0.1, color=color)
            ax.text(
                8.2, (low + high) / 2,
                f"UV {label}",
                fontsize=8,
                alpha=0.6,
                color=color,
                va='center',
            )

    def _get_peak_hours_range(
        self,
        times: List[int],
        uv_values: List[float],
    ) -> tuple:
        """获取高峰时段范围"""
        threshold = 5  # UV超过5视为高峰
        peak_times = [t for t, uv in zip(times, uv_values) if uv >= threshold]

        if not peak_times:
            return None, None

        return min(peak_times), max(peak_times)

    def generate_weekly_chart(
        self,
        week_data: List[Dict],
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        生成周UV趋势对比图

        Args:
            week_data: 一周的UV数据 [{date, max_uv, avg_uv}, ...]
            output_path: 图片保存路径

        Returns:
            str: 图片文件路径
        """
        if not week_data:
            logger.warning("无周数据，无法生成图表")
            return None

        dates = [d.get("date", "") for d in week_data]
        max_uvs = [d.get("max_uv", 0) for d in week_data]
        avg_uvs = [d.get("avg_uv", 0) for d in week_data]

        fig, ax = plt.subplots(figsize=(12, 6))

        # 绘制最高UV
        ax.bar(dates, max_uvs, alpha=0.7, color='red', label='最高UV')

        # 绘制平均UV
        ax.plot(dates, avg_uvs, 'b-', linewidth=2, marker='o', label='平均UV')

        ax.set_title("本周紫外线指数对比", fontsize=14, fontweight='bold')
        ax.set_xlabel("日期", fontsize=12)
        ax.set_ylabel("紫外线指数", fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if output_path is None:
            output_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data",
                "weekly_chart.png",
            )

        try:
            fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
            return output_path
        except Exception as e:
            logger.error(f"保存周图表失败: {e}")
            return None
        finally:
            plt.close(fig)


# 全局实例
_chart_generator: ChartGenerator = None


def get_chart_generator() -> ChartGenerator:
    """获取图表生成器实例"""
    global _chart_generator
    if _chart_generator is None:
        _chart_generator = ChartGenerator()
    return _chart_generator


def generate_uv_chart(weather_data: WeatherData) -> Optional[str]:
    """生成UV图表（便捷函数）"""
    return get_chart_generator().generate_uv_chart(weather_data)