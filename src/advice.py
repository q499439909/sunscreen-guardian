"""
智能生活建议引擎

根据天气数据（UV指数、气温、湿度等）生成个性化的：
- 防晒建议
- 穿搭建议
- 其他生活建议
"""
from typing import Dict, List, Tuple
from dataclasses import dataclass
import logging

from .weather import WeatherData

logger = logging.getLogger(__name__)


@dataclass
class LifeAdvice:
    """生活建议"""
    sunscreen: str  # 防晒建议
    outfit: str  # 穿搭建议
    other: str  # 其他建议
    items_to_carry: List[str]  # 出门建议携带物品


class AdviceEngine:
    """智能建议引擎"""

    def generate_advice(self, weather_data: WeatherData) -> LifeAdvice:
        """
        根据天气数据生成生活建议

        Args:
            weather_data: 天气数据

        Returns:
            LifeAdvice: 生活建议
        """
        # 防晒建议
        sunscreen = self._generate_sunscreen_advice(
            weather_data.max_uv,
            weather_data.temp_max,
            weather_data.peak_hours,
        )

        # 穿搭建议
        outfit = self._generate_outfit_advice(
            weather_data.weather,
            weather_data.temp_max,
            weather_data.wind_speed,
        )

        # 其他建议
        other = self._generate_other_advice(
            weather_data.temp_max,
            weather_data.temp_min,
            weather_data.humidity,
            weather_data.precipitation,
        )

        # 出门携带物品
        items = self._get_items_to_carry(
            weather_data.max_uv,
            weather_data.precipitation,
            weather_data.temp_max,
        )

        return LifeAdvice(
            sunscreen=sunscreen,
            outfit=outfit,
            other=other,
            items_to_carry=items,
        )

    def _generate_sunscreen_advice(
        self,
        max_uv: float,
        temp_max: float,
        peak_hours: str,
    ) -> str:
        """生成防晒建议"""
        # 根据UV指数和气温组合判断
        if max_uv <= 2:
            return "今日紫外线较弱，室内活动无需防晒，户外活动建议SPF15基础防护。"

        elif max_uv <= 5:
            if temp_max < 25:
                return "紫外线中等，建议涂抹SPF30防晒霜，长时间户外可配合遮阳帽。"
            else:
                return "紫外线中等+高温，建议SPF30防晒霜，注意补涂（每2小时），选择清爽型防晒。"

        elif max_uv <= 7:
            if temp_max < 25:
                return "紫外线较强！必须涂抹SPF50防晒霜，建议佩戴遮阳帽+太阳镜。高峰时段尽量减少户外活动。"
            else:
                return f"紫外线较强+高温！建议SPF50防晒霜，优先物理防晒（帽子、遮阳伞），减少户外时长。高峰时段（{peak_hours}）尽量避免外出。"

        elif max_uv <= 10:
            return "紫外线很强！务必使用SPF50+防晒霜+物理防护（遮阳伞、太阳镜），尽量避免10:00-16:00外出。"

        else:
            return "紫外线极高！强烈建议减少外出，外出时全面防护（防晒霜+遮阳伞+太阳镜+防晒衣）。"

    def _generate_outfit_advice(
        self,
        weather: str,
        temp_max: float,
        wind_speed: float,
    ) -> str:
        """生成穿搭建议"""
        # 判断天气类型
        is_sunny = "晴" in weather
        is_cloudy = "多云" in weather or "阴" in weather
        is_rainy = "雨" in weather
        is_windy = wind_speed > 20  # 风速大于20km/h视为大风

        # 组合判断
        if is_rainy:
            return "雨天：建议穿防水面料或带雨具，穿深色衣物不易显水渍，备一件轻薄外套。"

        if is_windy:
            return "大风天：避免穿宽松裙装，建议穿修身款或带防风外套，注意发型固定。"

        if is_sunny:
            if temp_max >= 30:
                return "高温晴天：建议穿轻薄透气面料（棉麻、速干），浅色系更凉爽，可选短袖/短裤/连衣裙，注意防晒衣或遮阳伞搭配。"
            elif temp_max >= 25:
                return "温暖晴天：T恤+休闲裤/裙装，可选薄款防晒衫，建议带遮阳帽备用。"
            elif temp_max >= 20:
                return "舒适晴天：长袖薄衫+休闲裤，早晚温差大建议带薄外套。"
            else:
                return "凉爽晴天：建议穿长袖+外套，可备一件薄毛衣或卫衣，注意保暖。"

        elif is_cloudy:
            if temp_max >= 25:
                return "多云高温：轻薄穿搭即可，紫外线反射仍需注意防晒，建议带遮阳伞备用。"
            else:
                return "多云凉爽：正常春秋穿搭，备一件外套以防天气转晴或转冷。"

        else:
            # 默认建议
            if temp_max >= 25:
                return f"今日气温{temp_max}°C，建议轻薄透气穿搭，注意防晒。"
            else:
                return f"今日气温{temp_max}°C，建议适当保暖穿搭。"

    def _generate_other_advice(
        self,
        temp_max: float,
        temp_min: float,
        humidity: float,
        precipitation: float,
    ) -> str:
        """生成其他生活建议"""
        advices = []

        # 气温相关
        if temp_max >= 35:
            advices.append("高温预警！多喝水，避免正午外出，室内保持通风，注意防暑。")
        elif temp_max >= 30:
            advices.append("天气炎热，建议随身带水，空调房注意保湿，运动避开高温时段。")
        elif temp_min < 5:
            advices.append("气温偏低，注意保暖，出门带暖饮，室内注意温度调节。")

        # 湿度相关
        if humidity >= 80:
            advices.append("湿度较高，体感闷热，建议穿透气面料，注意皮肤清洁防汗渍。")
        elif humidity <= 30:
            advices.append("空气干燥，注意皮肤保湿，多喝水，室内可用加湿器。")

        # 降水相关
        if precipitation >= 60:
            advices.append("降水概率较高，建议带伞出门，防晒霜可选防水款。")
        elif precipitation >= 30:
            advices.append("可能有雨，建议随身带轻便雨具。")

        if not advices:
            advices.append("今日天气舒适，适合户外活动。")

        return " ".join(advices)

    def _get_items_to_carry(
        self,
        max_uv: float,
        precipitation: float,
        temp_max: float,
    ) -> List[str]:
        """获取出门建议携带物品"""
        items = []

        # 防晒相关
        if max_uv > 3:
            items.append("防晒霜")
        if max_uv > 5:
            items.append("遮阳伞")
        if max_uv > 7:
            items.append("太阳镜")

        # 降水相关
        if precipitation >= 30:
            items.append("雨具")

        # 气温相关
        if temp_max >= 30:
            items.append("水杯")
        if temp_max <= 20:
            items.append("外套")

        # 默认建议
        if not items:
            items.append("手机")

        return items

    def format_advice_for_display(self, advice: LifeAdvice) -> Dict[str, str]:
        """
        格式化建议用于展示

        Args:
            advice: 生活建议

        Returns:
            Dict: 格式化的建议字典
        """
        # 格式化其他建议 + 携带物品
        other_text = advice.other
        if advice.items_to_carry:
            other_text += f"\n\n出门建议携带：{', '.join(advice.items_to_carry)}"

        return {
            "sunscreen": advice.sunscreen,
            "outfit": advice.outfit,
            "other": other_text,
        }


# 全局实例
_advice_engine: AdviceEngine = None


def get_advice_engine() -> AdviceEngine:
    """获取建议引擎实例"""
    global _advice_engine
    if _advice_engine is None:
        _advice_engine = AdviceEngine()
    return _advice_engine


def generate_life_advice(weather_data: WeatherData) -> Dict[str, str]:
    """生成生活建议（便捷函数）"""
    engine = get_advice_engine()
    advice = engine.generate_advice(weather_data)
    return engine.format_advice_for_display(advice)