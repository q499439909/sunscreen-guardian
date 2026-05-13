"""
天气API对接模块

使用Open-Meteo API（免费、无需API key、支持逐小时UV）
文档：https://open-meteo.com/en/docs
"""
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime, date
from dataclasses import dataclass
import logging

from .config_loader import get_config

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    """天气数据结构"""
    date: date
    city: str
    hourly_uv: List[Dict[str, Any]]
    max_uv: float
    peak_hours: str
    temp_min: float
    temp_max: float
    temp_now: float
    feels_like: float
    humidity: int
    weather: str
    weather_code: str
    wind_speed: float
    wind_dir: str
    precipitation: float
    pressure: float
    visibility: float


class OpenMeteoAPI:
    """Open-Meteo API客户端（免费、无需API key）"""

    # 中国主要城市坐标
    CITY_COORDS = {
        "深圳": (22.54, 114.06),
        "北京": (39.90, 116.41),
        "上海": (31.23, 121.47),
        "广州": (23.13, 113.26),
        "杭州": (30.27, 120.15),
        "成都": (30.57, 104.07),
        "武汉": (30.59, 114.31),
        "南京": (32.06, 118.80),
        "重庆": (29.56, 106.55),
        "西安": (34.26, 108.93),
        "天津": (39.08, 117.20),
        "苏州": (31.30, 120.62),
        "郑州": (34.75, 113.65),
        "长沙": (28.23, 112.94),
        "东莞": (23.02, 113.75),
        "青岛": (36.07, 120.38),
        "沈阳": (41.80, 123.43),
        "宁波": (29.87, 121.55),
        "昆明": (25.04, 102.71),
        "合肥": (31.82, 117.23),
    }

    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1"

    def get_weather_data(self, city_name: str) -> WeatherData:
        """获取完整的天气数据"""
        # 1. 获取城市坐标
        lat, lon = self._get_city_coords(city_name)

        # 2. 调用Open-Meteo API
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "uv_index,temperature_2m,weather_code,relative_humidity_2m,precipitation_probability,wind_speed_10m",
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "Asia/Shanghai",
            "forecast_days": 1,
        }

        url = f"{self.base_url}/forecast"
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        # 3. 解析数据
        return self._parse_weather_data(data, city_name)

    def _get_city_coords(self, city_name: str) -> tuple:
        """获取城市坐标"""
        # 移除市/区后缀
        clean_name = city_name.replace("市", "").replace("区", "")

        if clean_name in self.CITY_COORDS:
            return self.CITY_COORDS[clean_name]

        # 默认深圳
        logger.warning(f"未找到城市 {city_name} 坐标，使用默认（深圳）")
        return (22.54, 114.06)

    def _parse_weather_data(self, data: Dict, city_name: str) -> WeatherData:
        """解析天气数据"""
        today = date.today()

        # 当前天气
        current = data.get("current", {})
        temp_now = current.get("temperature_2m", 25)
        humidity = current.get("relative_humidity_2m", 50)
        weather_code = str(current.get("weather_code", 0))
        wind_speed = current.get("wind_speed_10m", 0)

        # 逐小时数据
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        uv_values = hourly.get("uv_index", [])
        temps = hourly.get("temperature_2m", [])
        weather_codes = hourly.get("weather_code", [])

        # 构建逐小时UV数据
        hourly_uv = []
        for i, t in enumerate(times):
            hour = int(t.split("T")[1].split(":")[0])
            hourly_uv.append({
                "time": f"{hour:02d}:00",
                "uv": round(uv_values[i] if i < len(uv_values) else 0, 1),
                "temp": round(temps[i] if i < len(temps) else temp_now, 1),
                "weather": self._weather_code_to_text(weather_codes[i] if i < len(weather_codes) else 0),
            })

        # 计算最高UV和温度范围
        max_uv = max(uv_values) if uv_values else 0
        temp_min = min(temps) if temps else temp_now
        temp_max = max(temps) if temps else temp_now

        # 高峰时段
        peak_hours = self._get_peak_hours(hourly_uv)

        return WeatherData(
            date=today,
            city=city_name,
            hourly_uv=hourly_uv,
            max_uv=round(max_uv, 1),
            peak_hours=peak_hours,
            temp_min=round(temp_min, 1),
            temp_max=round(temp_max, 1),
            temp_now=round(temp_now, 1),
            feels_like=round(temp_now, 1),
            humidity=humidity,
            weather=self._weather_code_to_text(int(weather_code)),
            weather_code=weather_code,
            wind_speed=round(wind_speed, 1),
            wind_dir="北",
            precipitation=0,
            pressure=1013,
            visibility=10,
        )

    def _weather_code_to_text(self, code: int) -> str:
        """WMO天气代码转文字"""
        weather_map = {
            0: "晴",
            1: "晴", 2: "多云", 3: "阴",
            45: "雾", 48: "雾",
            51: "小雨", 53: "小雨", 55: "中雨",
            61: "小雨", 63: "中雨", 65: "大雨",
            71: "小雪", 73: "中雪", 75: "大雪",
            80: "阵雨", 81: "阵雨", 82: "暴雨",
            95: "雷雨", 96: "雷雨", 99: "雷雨",
        }
        return weather_map.get(code, "晴")

    def _get_peak_hours(self, hourly_uv: List[Dict]) -> str:
        """获取UV高峰时段"""
        peak_times = []
        threshold = 5

        for h in hourly_uv:
            if h.get("uv", 0) >= threshold:
                peak_times.append(h.get("time", ""))

        if not peak_times:
            return "无明显高峰"

        if len(peak_times) <= 2:
            return ", ".join(peak_times)

        return f"{peak_times[0]} - {peak_times[-1]}"


# 全局实例
_weather_api: OpenMeteoAPI = None


def get_weather_api() -> OpenMeteoAPI:
    """获取天气API实例"""
    global _weather_api
    if _weather_api is None:
        _weather_api = OpenMeteoAPI()
    return _weather_api