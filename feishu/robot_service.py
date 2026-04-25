from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import os
import json
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import lark_oapi as lark
from lark_oapi.api.application.v6 import P2ApplicationBotMenuV6
from lark_oapi.api.im.v1 import *
from lark_oapi.api.im.v1 import P2ImChatAccessEventBotP2pChatEnteredV1, P2ImMessageReceiveV1
from lark_oapi.event.callback.model.p2_card_action_trigger import (
    P2CardActionTrigger,
    P2CardActionTriggerResponse,
)

from feishu.robot_utils import send_message, template_card_content, build_client, load_settings

@dataclass(frozen=True)
class BotTemplates:
    btc_news_chat_id: str
    common_card_id: str

def load_bot_templates() -> BotTemplates:
    btc_news_chat_id = os.getenv("FEISHU_BTCNEWS_CHAT_ID", "")
    common_card_id = os.getenv("FEISHU_COMMON_CARD_ID", "")

    if not btc_news_chat_id:
        raise ValueError("FEISHU_BTCNEWS_CHAT_ID is required")

    if not common_card_id:
        raise ValueError("FEISHU_COMMON_CARD_ID is required")

    return BotTemplates(
        btc_news_chat_id=btc_news_chat_id,
        common_card_id=common_card_id
    )

class MsgBotService:
    client: lark.Client
    templates: BotTemplates = load_bot_templates()

    def __init__(self, client: lark.Client = None):
        self.client = client or build_client(load_settings())
    
    def send_common_card(self, chat_id: str = templates.btc_news_chat_id, template_variable: dict = None):
        content = template_card_content(
            template_id=self.templates.common_card_id,
            template_variable=template_variable,
        )
        response: CreateMessageResponse = send_message(self.client, "chat_id", chat_id, "interactive", content)
        # 处理失败返回
        if not response.success():
            lark.logger.error(
                f"client.im.v1.message.create failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
            return

        # 处理业务结果
        lark.logger.info(f"client.im.v1.message.create success, msg_id: {response.data.message_id}")
        # lark.logger.debug(lark.JSON.marshal(response.data, indent=4))
    


@dataclass
class BotService:
    client: lark.Client
    templates: BotTemplates = load_bot_templates()

    def __init__(self, client):
        self.client = client

    # def send_welcome_card(self, open_id: str):
    #     content = template_card_content(
    #         template_id=self.templates.welcome_card_id,
    #         template_variable={"open_id": open_id},
    #     )
    #     return send_message(self.client, "open_id", open_id, "interactive", content)

    # def send_alarm_card(self, receive_id_type: str, receive_id: str):
    #     content = template_card_content(
    #         template_id=self.templates.alert_card_id,
    #         template_variable={"alarm_time": _now_utc8_str()},
    #     )
    #     return send_message(self.client, receive_id_type, receive_id, "interactive", content)

    def on_p2p_chat_entered(self, data: P2ImChatAccessEventBotP2pChatEnteredV1) -> None:
        print(f"[ onP2ChatAccessEventBotP2pChatEnteredV1 access ], data: {data}")
        # open_id = data.event.operator_id.open_id
        # self.send_welcome_card(open_id)

    def on_bot_menu(self, data: P2ApplicationBotMenuV6) -> None:
        print(f"[ onP2BotMenuV6 access ], data: {data}")
        # open_id = data.event.operator.operator_id.open_id
        # event_key = data.event.event_key

        # if event_key == "send_alarm":
        #     self.send_alarm_card("open_id", open_id)

    def on_message_receive(self, data: P2ImMessageReceiveV1) -> None:
        print(f"[ onP2MessageReceiveV1 access ], data: {data}")
        # chat_type = data.event.message.chat_type
        # chat_id = data.event.message.chat_id
        # open_id = data.event.sender.sender_id.open_id

        # if chat_type == "group":
        #     self.send_alarm_card("chat_id", chat_id)
        # elif chat_type == "p2p":
        #     self.send_alarm_card("open_id", open_id)

    def on_card_action(self, data: P2CardActionTrigger) -> P2CardActionTriggerResponse:
        print(f"[ P2CardActionTrigger access ], data: {data}")
        # open_id = data.event.operator.open_id
        # action = data.event.action

        # if action.value["action"] == "send_alarm":
        #     self.send_alarm_card("open_id", open_id)
        #     return P2CardActionTriggerResponse({})

        # if action.value["action"] == "complete_alarm":
        #     notes = ""
        #     if action.form_value and "notes_input" in action.form_value:
        #         notes = str(action.form_value["notes_input"])

        #     content = {
        #         "toast": {
        #             "type": "info",
        #             "content": "已处理完成！",
        #             "i18n": {"zh_cn": "已处理完成！", "en_us": "Resolved!"},
        #         },
        #         "card": {
        #             "type": "template",
        #             "data": {
        #                 "template_id": self.templates.alert_resolved_card_id,
        #                 "template_variable": {
        #                     "alarm_time": action.value["time"],
        #                     "open_id": open_id,
        #                     "complete_time": _now_utc8_str(),
        #                     "notes": notes,
        #                 },
        #             },
        #         },
        #     }
        #     return P2CardActionTriggerResponse(content)

        return P2CardActionTriggerResponse(
            {
                "toast": {
                    "type": "error",
                    "content": "Unknown action",
                    "i18n": {"zh_cn": "未知操作", "en_us": "Unknown action"},
                }
            }
        )

# 监听交互事件
def build_event_handler(bot: BotService) -> lark.EventDispatcherHandler:
    return (
        lark.EventDispatcherHandler.builder("", "")
        # .register_p2_im_chat_access_event_bot_p2p_chat_entered_v1(bot.on_p2p_chat_entered)
        # .register_p2_application_bot_menu_v6(bot.on_bot_menu)
        # .register_p2_im_message_receive_v1(bot.on_message_receive)
        .register_p2_card_action_trigger(bot.on_card_action)
        .build()
    )