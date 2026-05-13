"""
飞书消息推送模块

飞书开放平台文档：https://open.feishu.cn/document/

主要功能：
- 消息推送（通过Webhook）
- 消息接收（通过回调）
- 图片上传
"""
import requests
import json
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import logging
import base64
import hashlib
import time
import hmac

from .config_loader import get_config

logger = logging.getLogger(__name__)


@dataclass
class FeishuMessage:
    """飞书消息结构"""
    title: str
    content: str
    image_key: Optional[str] = None
    elements: Optional[List[Dict]] = None


class FeishuAPI:
    """飞书API客户端"""

    def __init__(self):
        import os
        self.config = get_config()
        self.webhook_url = os.environ.get("FEISHU_WEBHOOK_URL") or self.config.feishu.webhook_url
        self.app_id = self.config.feishu.app_id
        self.app_secret = self.config.feishu.app_secret
        self._access_token: Optional[str] = None
        self._token_expire_time: int = 0

    def _get_access_token(self) -> str:
        """获取飞书应用访问令牌"""
        if self._access_token and time.time() < self._token_expire_time:
            return self._access_token

        if not self.app_id or not self.app_secret:
            logger.warning("飞书应用ID或Secret未配置，无法获取access_token")
            return ""

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0:
                self._access_token = result.get("tenant_access_token")
                self._token_expire_time = time.time() + result.get("expire", 7200) - 300
                return self._access_token
            else:
                logger.error(f"获取access_token失败: {result}")
                return ""

        except Exception as e:
            logger.error(f"获取access_token异常: {e}")
            return ""

    def send_webhook_message(self, message: FeishuMessage) -> bool:
        """
        通过Webhook发送消息（适用于群机器人）

        Args:
            message: 消息内容

        Returns:
            bool: 是否发送成功
        """
        if not self.webhook_url:
            logger.error("飞书Webhook URL未配置")
            return False

        # 构建消息卡片
        card = self._build_message_card(message)

        payload = {
            "msg_type": "interactive",
            "card": card,
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("StatusCode") == 0 or result.get("code") == 0:
                logger.info("飞书消息发送成功")
                return True
            else:
                logger.error(f"飞书消息发送失败: {result}")
                return False

        except Exception as e:
            logger.error(f"飞书消息发送异常: {e}")
            return False

    def _build_message_card(self, message: FeishuMessage) -> Dict:
        """构建飞书消息卡片"""
        elements = []

        # 添加文本内容
        if message.content:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": message.content,
                }
            })

        # 添加图片
        if message.image_key:
            elements.append({
                "tag": "img",
                "img_key": message.image_key,
                "alt": {
                    "tag": "plain_text",
                    "content": "紫外线指数趋势图",
                },
                "mode": "fit_horizontal",
            })

        # 添加自定义元素
        if message.elements:
            elements.extend(message.elements)

        card = {
            "config": {
                "wide_screen_mode": True,
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": message.title,
                },
                "template": self._get_header_color(message.title),
            },
            "elements": elements,
        }

        return card

    def _get_header_color(self, title: str) -> str:
        """根据消息标题获取头部颜色"""
        if "日报" in title:
            return "blue"
        elif "提醒" in title or "警告" in title:
            return "red"
        elif "周报" in title or "月报" in title:
            return "turquoise"
        elif "打卡" in title:
            return "green"
        else:
            return "blue"

    def upload_image(self, image_path: str) -> Optional[str]:
        """
        上传图片到飞书

        Args:
            image_path: 图片文件路径

        Returns:
            str: 图片key
        """
        access_token = self._get_access_token()
        if not access_token:
            logger.error("无法获取access_token，图片上传失败")
            return None

        url = "https://open.feishu.cn/open-apis/im/v1/images"

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        try:
            with open(image_path, "rb") as f:
                files = {
                    "image": (image_path, f, "image/png"),
                }
                data = {
                    "image_type": "message",
                }

                response = requests.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=30,
                )
                response.raise_for_status()
                result = response.json()

                if result.get("code") == 0:
                    image_key = result.get("data", {}).get("image_key")
                    logger.info(f"图片上传成功: {image_key}")
                    return image_key
                else:
                    logger.error(f"图片上传失败: {result}")
                    return None

        except Exception as e:
            logger.error(f"图片上传异常: {e}")
            return None

    def send_text_message(self, text: str) -> bool:
        """发送简单文本消息"""
        payload = {
            "msg_type": "text",
            "content": {
                "text": text,
            }
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            return response.json().get("StatusCode") == 0

        except Exception as e:
            logger.error(f"发送文本消息异常: {e}")
            return False


class MessageBuilder:
    """消息构建器"""

    def build_daily_report(
        self,
        weather_data,
        advice: Dict[str, str],
        stats: Dict[str, Any],
    ) -> FeishuMessage:
        """构建日报消息"""
        date_str = weather_data.date.strftime("%Y-%m-%d")

        # 构建内容
        content_parts = [
            f"📍 **当前城市**：{weather_data.city}",
            "",
            "🌡️ **今日天气概况**：",
            f"🔸 天气：{weather_data.weather}",
            f"🔸 温度：{weather_data.temp_min}°C ~ {weather_data.temp_max}°C",
            f"🔸 体感：{weather_data.feels_like}°C",
            f"🔸 湿度：{weather_data.humidity}%",
            f"🔸 降水概率：{weather_data.precipitation}%",
            "",
            "📊 **紫外线指数**：",
            f"🔸 最高UV指数：{weather_data.max_uv}",
            f"🔸 高峰时段：{weather_data.peak_hours}",
            "",
            "💡 **今日生活建议**：",
            "━━━━━━━━━━━━━━━━━━",
            f"🧴 **防晒建议**：\n{advice.get('sunscreen', '')}",
            "",
            f"👗 **穿搭建议**：\n{advice.get('outfit', '')}",
            "",
            f"☕ **其他提示**：\n{advice.get('other', '')}",
            "━━━━━━━━━━━━━━━━━━",
            "",
            self._build_warning(weather_data.max_uv),
            "",
            "─────────────────",
            f"📅 打卡记录：已连续 **{stats.get('continuous_days', 0)}** 天 ✅",
            f"🏆 累计防护：**{stats.get('total_days', 0)}** 天",
        ]

        content = "\n".join(content_parts)

        return FeishuMessage(
            title=f"☀️ 防晒管家日报 - {date_str}",
            content=content,
        )

    def _build_warning(self, max_uv: float) -> str:
        """构建警告提示"""
        if max_uv > 8:
            return "⚠️ **紫外线很强！务必做好防护！**"
        elif max_uv > 5:
            return "⚠️ **紫外线较强，请涂抹防晒霜！**"
        elif max_uv > 3:
            return "⚠️ **今日紫外线中等，建议做好防晒。**"
        else:
            return "💡 今日紫外线较弱，但仍建议基础防护。"

    def build_checkin_feedback(
        self,
        continuous_days: int,
        total_days: int,
        max_continuous: int,
        protection_value: float,
    ) -> FeishuMessage:
        """构建打卡反馈消息"""
        content_parts = [
            "🎉 **打卡成功！**",
            "",
            "📈 **你的防晒战绩**：",
            f"✅ 连续打卡：第 **{continuous_days}** 天",
            f"🏆 累计防护：**{total_days}** 天",
            f"🔥 历史最长：**{max_continuous}** 天",
            "",
            "💪 **今日防护效果**：",
            f"抵御了 **{protection_value:.1f}** 单位紫外线伤害",
            "",
            "💪 继续坚持，皮肤正在感谢你～",
        ]

        content = "\n".join(content_parts)

        return FeishuMessage(
            title="🎉 打卡成功",
            content=content,
        )

    def build_weekly_report(
        self,
        week_stats: Dict[str, Any],
        week_weather: Dict[str, Any],
        protection_result: Dict[str, Any],
        next_week_preview: str,
    ) -> FeishuMessage:
        """构建周报消息"""
        content_parts = [
            "📊 **本周天气概况**：",
            f"🌡️ 平均气温：{week_weather.get('avg_temp', 0)}°C",
            f"☀️ 晴天天数：{week_weather.get('sunny_days', 0)} 天",
            f"🌧️ 雨天天数：{week_weather.get('rainy_days', 0)} 天",
            "",
            "🏆 **本周战况**：",
            f"✅ 完成打卡：{week_stats.get('completed_days', 0)}/{week_stats.get('total_days', 7)} 天",
            f"📈 打卡率：{week_stats.get('completion_rate', 0):.0%}",
            f"🔥 最长连续：{week_stats.get('max_continuous', 0)} 天",
            "",
            "🛡️ **防护成果**：",
            f"累计防护值：{protection_result.get('total_protection', 0):.1f} 单位",
            f"避免晒黑风险：{protection_result.get('sunburn_risk_reduce', 0):.0%}",
            f"节省护肤成本：¥{protection_result.get('saved_cost', 0):.0f}",
            "",
            "📅 **下周天气预览**：",
            next_week_preview,
            "",
            "下周目标：保持节奏，继续加油！",
        ]

        content = "\n".join(content_parts)

        return FeishuMessage(
            title="📊 防晒管家周报",
            content=content,
        )


# 全局实例
_feishu_api: FeishuAPI = None
_message_builder: MessageBuilder = None


def get_feishu_api() -> FeishuAPI:
    """获取飞书API实例"""
    global _feishu_api
    if _feishu_api is None:
        _feishu_api = FeishuAPI()
    return _feishu_api


def get_message_builder() -> MessageBuilder:
    """获取消息构建器实例"""
    global _message_builder
    if _message_builder is None:
        _message_builder = MessageBuilder()
    return _message_builder