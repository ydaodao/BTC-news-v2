from dataclasses import dataclass
import json
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os

import lark_oapi as lark
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody


@dataclass(frozen=True)
class AppSettings:
    base_domain: str | None
    app_id: str
    app_secret: str

def load_settings() -> AppSettings:
    app_id = os.getenv("FEISHU_APP_DAODAO_BTCNEWS_ID")
    app_secret = os.getenv("FEISHU_APP_DAODAO_BTCNEWS_SECRET")

    if not app_id:
        raise ValueError("FEISHU_APP_DAODAO_BTCNEWS_ID is required")
    if not app_secret:
        raise ValueError("FEISHU_APP_DAODAO_BTCNEWS_SECRET is required")

    return AppSettings(
        base_domain=os.getenv("FEISHU_BASE_DOMAIN"),
        app_id=app_id,
        app_secret=app_secret,
    )

def build_client(settings: AppSettings) -> lark.Client:
    return lark.Client.builder().app_id(settings.app_id).app_secret(settings.app_secret).log_level(lark.LogLevel.INFO).build()


def build_ws_client(
    settings: AppSettings,
    event_handler: lark.EventDispatcherHandler,
    log_level: lark.LogLevel = lark.LogLevel.DEBUG,
) -> lark.ws.Client:
    return lark.ws.Client(
        settings.app_id,
        settings.app_secret,
        event_handler=event_handler,
        log_level=log_level,
    )


def send_message(
    client: lark.Client,
    receive_id_type: str,
    receive_id: str,
    msg_type: str,
    content: str,
):
    request = (
        CreateMessageRequest.builder()
        .receive_id_type(receive_id_type)
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(receive_id)
            .msg_type(msg_type)
            .content(content)
            .build()
        )
        .build()
    )

    response = client.im.v1.message.create(request)
    if not response.success():
        raise Exception(
            f"client.im.v1.message.create failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}"
        )
    return response


def template_card_content(template_id: str, template_variable: dict) -> str:
    return json.dumps(
        {
            "type": "template",
            "data": {
                "template_id": template_id,
                "template_variable": template_variable,
            },
        }
    )
