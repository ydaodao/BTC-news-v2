import os
import requests

def send_interactive_card(template_id: str, template_variable: dict, webhook_url: str = None):
    """
    发送飞书交互卡片到 webhook 机器人。
    """
    webhook_url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        print("错误：请设置 FEISHU_WEBHOOK_URL 环境变量或传入 webhook_url 参数")
        return

    message = {
        "msg_type": "interactive",
        "card": {
            "type": "template",
            "data": {
                "template_id": template_id,
                "template_variable": template_variable,
            },
        },
    }

    try:
        response = requests.post(
            webhook_url,
            json=message,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()

        result = response.json()
        print(f"飞书推送响应: {result}")

        if result.get("StatusCode") == 0:
            print("消息推送到飞书成功！")
        else:
            print(f"推送失败: {result.get('msg', '未知错误')}")
    except requests.exceptions.RequestException as e:
        print(f"消息推送到飞书失败：{e}")


if __name__ == "__main__":
    send_interactive_card(
        template_id="AAqeoJVruijGV",
        template_variable={
            "card_title": "测试卡片",
            "list": [
                {
                    "title": "测试标题",
                    "title_url": "https://www.baidu.com",
                    "desc": "测试描述",
                }
            ]
        },
        webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/424824fb-f84e-4f2a-8082-552c7f338cd8",
    )
