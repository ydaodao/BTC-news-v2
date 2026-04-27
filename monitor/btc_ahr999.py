from playwright.sync_api import Page
import time
from loguru import logger
from playwright.sync_api import sync_playwright, Playwright
from utils.playwright_utils import open_page, find_element, save_screenshot
from utils.file_utils import FileUtils
from feishu.robot_utils import build_client, load_settings
from feishu.robot_service import MsgBotService
from feishu.message_utils import upload_image
from utils.date_utils import DateUtils

# ========================
# 1. 配置区（你只需要改这里）
# ========================
# CONFIG = {
#     "monitor_url": "https://api.coingecko.com/api/v3/coins/bitcoin",  # 示例API
#     "interval": 60,  # 每60秒抓一次
# }

# ========================
# 2. 抓取数据
# ========================
def fetch_and_push_ahr999_img():
    logger.info("获取ahr999趋势的网页截图")
    image_path = None
    latest_data = None
    with sync_playwright() as p:
        p: Playwright
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        url = 'https://www.coinglass.com/zh/pro/i/ahr999'
        page = open_page(context, url)

        # 获取指标图
        ele_ahr999_img = find_element(page, ("ahr999指标图", "canvas"))
        image_path = FileUtils.get_path("images", "canvas.png")
        save_screenshot(ele_ahr999_img, image_path)
        logger.info(f"最新指标图: {image_path}")

        # 获取最新数据
        latest_data = parse_ahr999_data(page)

        page.close()
    
    if image_path:
        client = build_client(load_settings())
        image_key = upload_image(client, image_path)
        if image_key:
            bot = MsgBotService()
            logger.info("发送ahr999趋势的网页截图")
            template_variable = {
                "card_title": f'{DateUtils.now_str(fmt="%m.%d")} 加密数据',
                "card_desc": latest_data,
                "img_key": {
                    "img_key": image_key
                }
            }
            bot.send_common_card(template_variable=template_variable)

def parse_ahr999_data(page: Page):
    """解析ahr999数据"""
    ele_ahr999_latest_data = find_element(page, ("最近的ahr999数据", "div.ant-table-body > table > tbody > tr:nth-child(2)"))
    tr_date = find_element(ele_ahr999_latest_data, ("时间", "td:nth-child(1)")).text_content()
    tr_ahr999 = find_element(ele_ahr999_latest_data, ("ahr999囤币指标", "td:nth-child(2)")).text_content()
    tr_btc_price = find_element(ele_ahr999_latest_data, ("BTC价格", "td:nth-child(3)")).text_content().replace("$", "")
    tr_avg_cost = find_element(ele_ahr999_latest_data, ("200日定投成本", "td:nth-child(4)")).text_content()

    date = DateUtils.str_to_str(tr_date, from_fmt="%Y/%m/%d", to_fmt="%m.%d")
    ahr999 = round(float(tr_ahr999), 4)
    avg_cost = int(float(tr_avg_cost))
    btc_price = int(float(tr_btc_price))

    latest_data = f"${btc_price}    AHR999：{ahr999}"
    logger.info(f"最新数据: {latest_data}")
    return latest_data

# ========================
# 3. 解析你需要的指标
# ========================
# def parse_data(data):
    

# ========================
# 4. 保存到CSV（历史记录）
# ========================
# def save_to_csv(result):

# ========================
# 5. 主循环（定时运行）
# ========================
def main():
    fetch_and_push_ahr999_img()

if __name__ == "__main__":
    main()