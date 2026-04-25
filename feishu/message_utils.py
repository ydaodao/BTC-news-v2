import json

import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from feishu.robot_utils import build_client, load_settings
from utils.file_utils import FileUtils


def upload_image(
    client: lark.Client,
    image_file: str,
) -> CreateImageResponse:
    """上传图片到飞书"""
    # 构造请求对象
    file = open(image_file, "rb")
    request: CreateImageRequest = CreateImageRequest.builder() \
        .request_body(CreateImageRequestBody.builder()
            .image_type("message")
            .image(file)
            .build()) \
        .build()

    # 发起请求
    response: CreateImageResponse = client.im.v1.image.create(request)

    # 处理失败返回
    if not response.success():
        lark.logger.error(
            f"client.im.v1.image.create failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
        return

    # 处理业务结果
    lark.logger.info(lark.JSON.marshal(response.data, indent=4))
    return response.data.image_key

if __name__ == "__main__":
    settings = load_settings()
    client = build_client(settings)
    image_file = FileUtils.get_path("images", "canvas.png")
    data = upload_image(client, image_file)
    print(data)
