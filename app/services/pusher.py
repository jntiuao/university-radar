import os
import logging
import requests

logger = logging.getLogger('RadarApp')

def format_push_message(event, fmt="text"):
    """格式化推送消息内容 —— 微型情报简报"""
    uni = event.get('university', '')
    module = event.get('module', '')
    title = event.get('title', '')
    category = event.get('category', '通知')
    major = event.get('major', '')
    urgency = event.get('urgency', '中')
    score = event.get('relevance_score', 50)
    reason = event.get('relevance_reason', '')
    summary = event.get('ai_summary', '')
    action = event.get('ai_action') or event.get('ai_action_suggestion') or ''
    link = event.get('link', '')
    date = event.get('publish_date', '')

    urgency_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(urgency, "⚪")
    stars = "⭐" * max(1, round(score / 20))

    if fmt == "html":
        actions_html = "".join([f"<li style='margin-bottom: 5px;'>{a.strip()}</li>" for a in action.split(";") if a.strip()])
        return f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
    <div style="background-color: #f8f9fa; padding: 15px 20px; border-bottom: 2px solid #6c5ce7;">
        <h3 style="margin: 0; color: #333; font-size: 18px;">🎓 {uni} <span style="color: #666; font-weight: normal; font-size: 16px;">· {module}</span></h3>
    </div>
    <div style="padding: 20px;">
        <h4 style="margin: 0 0 15px 0; font-size: 17px; color: #2d3436; line-height: 1.4;">📌 {title}</h4>

        <div style="background-color: #f1f2f6; padding: 12px 15px; border-radius: 6px; margin-bottom: 18px; font-size: 14px; color: #2d3436;">
            <span style="display: inline-block; padding: 4px 10px; background: #fff; border-radius: 4px; border: 1px solid #dcdde1; margin-right: 8px; font-weight: 500;">🏷️ {category}</span>
            <span style="display: inline-block; padding: 4px 10px; background: #fff; border-radius: 4px; border: 1px solid #dcdde1; margin-right: 8px; font-weight: 500;">📖 {major}</span>
            <span style="display: inline-block; padding: 4px 10px; background: #fff; border-radius: 4px; border: 1px solid #dcdde1; font-weight: 500; color: #d63031;">{urgency_icon} {urgency}</span>
        </div>

        <div style="margin-bottom: 18px; padding: 12px 15px; border: 1px solid #e1b12c; background-color: #fcf6e8; border-radius: 6px;">
            <p style="margin: 0 0 6px 0; font-size: 15px; color: #2d3436; font-weight: bold;">📊 相关度：<span style="color: #6c5ce7;">{score}%</span> {stars}</p>
            <p style="margin: 0; font-size: 14px; color: #b33939;">🎯 {reason}</p>
        </div>

        <div style="background-color: #f8f0fc; border-left: 4px solid #a29bfe; padding: 15px; border-radius: 0 6px 6px 0; margin-bottom: 20px;">
            <p style="margin: 0 0 8px 0; font-size: 14px; color: #2d3436; font-weight: bold;">🧠 AI 深度解读</p>
            <p style="margin: 0; font-size: 14px; color: #444; line-height: 1.6;">{summary}</p>
        </div>

        <div style="margin-bottom: 25px; background-color: #fcfcfc; padding: 15px; border: 1px dashed #ced6e0; border-radius: 6px;">
            <p style="margin: 0 0 10px 0; font-size: 14px; color: #2d3436; font-weight: bold;">💡 行动建议提取</p>
            <ul style="margin: 0; padding-left: 20px; font-size: 14px; color: #444; line-height: 1.7;">
                {actions_html}
            </ul>
        </div>

        <div style="text-align: center; margin-top: 10px; padding-top: 20px; border-top: 1px solid #f1f2f6;">
            <p style="margin: 0 0 15px 0; color: #7f8fa6; font-size: 12px;">📅 发布时间：{date}</p>
            <a href="{link}" target="_blank" style="display: inline-block; background-color: #6c5ce7; color: #ffffff; text-decoration: none; padding: 10px 24px; border-radius: 50px; font-size: 14px; font-weight: 600; box-shadow: 0 2px 4px rgba(108, 92, 231, 0.3);">🔗 点击查看官方原文</a>
        </div>
    </div>
</div>
"""
    else:
        actions_text = "\n".join([f"   {i+1}. {a.strip()}" for i, a in enumerate(action.split(";")) if a.strip()])
        return f"""🎓 {uni} · {module}
━━━━━━━━━━━━━━━━━━
📌 {title}

🏷️ {category} | {major} | {urgency_icon} {urgency}
📊 相关度：{stars} ({score}%) — {reason}

🧠 AI 解读：{summary}

💡 下一步建议：
{actions_text}

📅 {date}
🔗 {link}"""

def push_to_channel(channel_config, event, proxy=None):
    """向单个渠道推送消息"""
    channel = channel_config.get('channel', '')
    token = channel_config.get('token', '')

    if not channel or not token:
        return False

    try:
        req_proxies = {"http": proxy, "https": proxy} if proxy else None

        if channel == 'feishu':
            uni = event.get('university', '')
            module = event.get('module', '')
            title = event.get('title', '')
            category = event.get('category', '通知')
            major = event.get('major', '')
            urgency = event.get('urgency', '中')
            score = event.get('relevance_score', 50)
            reason = event.get('relevance_reason', '')
            summary = event.get('ai_summary', '')
            action = event.get('ai_action') or event.get('ai_action_suggestion') or ''
            link = event.get('link', '')

            urgency_color = "red" if urgency == "高" else ("orange" if urgency == "中" else "green")
            actions_text = "\n".join([f"- {a.strip()}" for a in action.split(";") if a.strip()])

            payload = {
                "msg_type": "interactive",
                "card": {
                    "config": { "wide_screen_mode": True },
                    "header": {
                        "template": urgency_color,
                        "title": { "content": f"🎯 【{category}】{uni} {module}", "tag": "plain_text" }
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": f"**📌 {title}**\n\n**🏷️ 标签：** {category} | {major}\n**📊 相关度：** {score}% — {reason}"
                        },
                        { "tag": "hr" },
                        {
                            "tag": "markdown",
                            "content": f"**🧠 AI 深度解读**\n{summary}"
                        },
                        {
                            "tag": "markdown",
                            "content": f"**💡 下一步建议行动**\n{actions_text}"
                        },
                        {
                            "tag": "action",
                            "actions": [
                                {
                                    "tag": "button",
                                    "text": { "content": "🔗 点击查看官方原文", "tag": "plain_text" },
                                    "type": "primary",
                                    "url": link
                                }
                            ]
                        }
                    ]
                }
            }
            resp = requests.post(token, json=payload, timeout=10, proxies=req_proxies)
            return resp.status_code == 200

        elif channel == 'email':
            from .email_notifier import EmailNotifier
            parts = token.split(",")
            if len(parts) >= 3:
                sender, password, receiver = parts[0].strip(), parts[1].strip(), parts[2].strip()
            else:
                return False
            em = EmailNotifier(sender, password)
            title = f"🎯 {event.get('university', '')} - {event.get('title', '')[:40]}"
            html = format_push_message(event, "html")
            return em.send_message(receiver, title, html)

    except Exception as e:
        logger.error(f"推送到 {channel} 发生严重异常: {e}")
        return False
