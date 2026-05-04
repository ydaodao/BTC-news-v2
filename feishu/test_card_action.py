from feishu.robot_service import BotService, MsgBotService, build_event_handler, load_bot_templates
from feishu.robot_utils import build_client, build_ws_client, load_settings
from loguru import logger

logger.info("Starting bot...")
settings = load_settings()
client = build_client(settings)

def ws_client_start():
    bot = BotService(client=client)
    event_handler = build_event_handler(bot)
    ws_client = build_ws_client(settings, event_handler=event_handler)

    ws_client.start()

def test_send_general_card():
    logger.info("Testing send_general_card...")
    template_variable = {
        "card_title": "测试标题",
        "card_desc": "测试内容",
        "img_key": {
            "img_key": "img_v3_02113_df89bf5d-4a35-4a93-b717-87ea8bcb014g"
        }
    }
    msg_bot = MsgBotService(client=client)
    msg_bot.send_general_card(template_variable=template_variable)
    logger.info("send_general_card success")

if __name__ == "__main__":
    # ws_client_start()
    test_send_general_card()
