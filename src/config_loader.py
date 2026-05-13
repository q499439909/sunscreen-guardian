"""
配置加载模块
"""
import os
import yaml
from pathlib import Path
from typing import Any
from pydantic import BaseModel


class WeatherConfig(BaseModel):
    api_key: str
    base_url: str = "https://devapi.qweather.com/v7"


class FeishuConfig(BaseModel):
    webhook_url: str
    app_id: str = ""
    app_secret: str = ""


class SchedulerConfig(BaseModel):
    daily_push_time: str = "08:00"
    weekly_report_day: str = "Sunday"
    weekly_report_time: str = "20:00"
    monthly_report_day: int = 1
    monthly_report_time: str = "20:00"


class DatabaseConfig(BaseModel):
    type: str = "sqlite"
    path: str = "./data/sunscreen.db"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "./logs/app.log"


class UserConfig(BaseModel):
    default_city: str = "北京"


class Config(BaseModel):
    weather: WeatherConfig
    feishu: FeishuConfig
    scheduler: SchedulerConfig
    database: DatabaseConfig
    logging: LoggingConfig
    user: UserConfig


def load_config(config_path: str = None) -> Config:
    """加载配置文件，支持环境变量降级"""
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "config.yaml"
        )

    config_path = Path(config_path)

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        return Config(**config_data)

    # 无配置文件时，从环境变量构建
    return Config(
        weather=WeatherConfig(
            api_key=os.environ.get("WEATHER_API_KEY", ""),
            base_url=os.environ.get("WEATHER_BASE_URL", "https://devapi.qweather.com/v7"),
        ),
        feishu=FeishuConfig(
            webhook_url=os.environ.get("FEISHU_WEBHOOK_URL", ""),
            app_id=os.environ.get("FEISHU_APP_ID", ""),
            app_secret=os.environ.get("FEISHU_APP_SECRET", ""),
        ),
        scheduler=SchedulerConfig(),
        database=DatabaseConfig(),
        logging=LoggingConfig(),
        user=UserConfig(
            default_city=os.environ.get("DEFAULT_CITY", "深圳"),
        ),
    )


# 全局配置实例
_config: Config = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: str = None) -> Config:
    """重新加载配置"""
    global _config
    _config = load_config(config_path)
    return _config