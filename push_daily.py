"""
防晒管家 - 每日推送脚本

独立运行，无需 Web 服务/数据库/打卡系统。
通过 GitHub Actions 每天早上 8 点（北京时间）自动触发。
"""
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(__file__))

from src.weather import get_weather_api
from src.advice import get_advice_engine
from src.chart import get_chart_generator
from src.feishu import get_feishu_api, get_message_builder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    city = os.environ.get("DEFAULT_CITY", "深圳")
    logger.info(f"开始每日推送: {city}")

    # 1. 获取天气数据
    weather_api = get_weather_api()
    weather_data = weather_api.get_weather_data(city)
    logger.info(f"天气: {weather_data.weather}, UV: {weather_data.max_uv}")

    # 2. 生成生活建议
    advice_engine = get_advice_engine()
    advice = advice_engine.generate_advice(weather_data)
    formatted_advice = advice_engine.format_advice_for_display(advice)

    # 3. 生成折线图
    chart_gen = get_chart_generator()
    chart_path = chart_gen.generate_uv_chart(weather_data)
    logger.info(f"图表: {chart_path}")

    # 4. 上传图片 + 发送消息
    feishu = get_feishu_api()
    image_key = None
    if chart_path:
        image_key = feishu.upload_image(chart_path)
        logger.info(f"图片已上传: {image_key}")

    builder = get_message_builder()
    message = builder.build_daily_report(
        weather_data=weather_data,
        advice=formatted_advice,
        stats={"continuous_days": 0, "total_days": 0},
    )
    message.image_key = image_key

    success = feishu.send_webhook_message(message)

    if success:
        logger.info("推送成功")
    else:
        logger.error("推送失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
