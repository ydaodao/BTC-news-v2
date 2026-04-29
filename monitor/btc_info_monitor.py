import re
from playwright.sync_api import Page
import time
from loguru import logger
from playwright.sync_api import sync_playwright, Playwright, BrowserContext
from utils.playwright_utils import open_page, find_element, save_screenshot
from utils.file_utils import FileUtils
from feishu.robot_utils import build_client, load_settings
from feishu.robot_service import MsgBotService
from feishu.message_utils import upload_image
from utils.date_utils import DateUtils
import lark_oapi as lark

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
def fetch_and_push_btc_info():
    logger.info("获取BTC信息")
    client = build_client(load_settings())
    ahr999_image_key, ahr999_latest_data = None, None
    pm_clarity_image_key, pm_clarity_latest_data = None, None

    with sync_playwright() as p:
        p: Playwright
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        context.set_default_timeout(60000)
        
        ahr999_latest_data, ahr999_image_key = fetch_ahr999_info(context, client)
        pm_clarity_latest_data, pm_clarity_image_key = fetch_pm_clarity_info(context, client)
        calshi_clarity_latest_data, calshi_clarity_image_key = fetch_calshi_clarity_info(context, client)
        
    if ahr999_image_key:
        bot = MsgBotService()
        logger.info("发送ahr999趋势的网页截图")
        template_variable = {
            "card_title": f'{DateUtils.now_str(fmt="%m.%d")} 加密数据',
            "ahr999_desc": ahr999_latest_data,
            "ahr999_img_key": {
                "img_key": ahr999_image_key
            },
            "pm_clarity_desc": pm_clarity_latest_data,
            "pm_clarity_img_key": {
                "img_key": pm_clarity_image_key
            },
            "calshi_clarity_desc": calshi_clarity_latest_data,
            "calshi_clarity_img_key": {
                "img_key": calshi_clarity_image_key
            },
            "primary_btn_text": "待定",
            "secondary_btn_text": "待定",
        }
        bot.send_common_card(template_variable=template_variable)

def fetch_ahr999_info(context: BrowserContext, client: lark.Client):
    """获取ahr999数据"""
    url = 'https://www.coinglass.com/zh/pro/i/ahr999'
    page = open_page(context, url)

    # 获取指标图
    ele_ahr999_img = find_element(page, ("ahr999指标图", "canvas"))
    image_path = FileUtils.get_path("images", "canvas.png")
    save_screenshot(ele_ahr999_img, image_path)
    image_key = upload_image(client, image_path)
    logger.info(f"最新指标图: {image_path}, {image_key}")

    # 获取最新数据
    latest_data = parse_ahr999_data(page)

    page.close()
    return latest_data, image_key

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

    latest_data = f"AHR999：{ahr999}    BTC价格：${btc_price}"
    logger.info(f"最新数据: {latest_data}")
    return latest_data

def fetch_pm_clarity_info(context: BrowserContext, client: lark.Client):
    """获取pm clarity数据"""
    url = 'https://polymarket.com/zh/event/clarity-act-signed-into-law-in-2026'
    page = open_page(context, url)

    # 获取指标图
    ele_pm_clarity_img = find_element(page, ("pm clarity指标图", "#group-chart-container")).locator("..")
    image_path = FileUtils.get_path("images", "pm_clarity.png")
    save_screenshot(ele_pm_clarity_img, image_path)
    image_key = upload_image(client, image_path)
    logger.info(f"pm clarity指标图: {image_path}, {image_key}")

    # 获取最新概率数据
    target_locator = (
        page.locator("span", has_text="% 概率")
        .locator("..")
        .locator("..")
        .locator("xpath=preceding-sibling::span[1]")
    )
    target_locator.highlight()  # 调试时很有用，会让元素闪烁
    logger.info(f"polymarket概率: {target_locator.inner_text()}%")
    latest_data = f"PM概率: {target_locator.inner_text()}%"
    # 操作该元素

    page.close()
    return latest_data, image_key

def fetch_calshi_clarity_info(context: BrowserContext, client: lark.Client):
    """获取calshi clarity数据"""
    url = 'https://kalshi.com/markets/kxcryptostructure/crypto-market-structure/kxcryptostructure-26jan'
    page = open_page(context, url)
    # 获取锚点
    vol_anchor = page.locator("span").filter(has_text=re.compile(r"\$.*vol"))

    # 获取calshi clarity预测趋势图
    calshi_clarity_chart = vol_anchor.locator("..").locator("..").locator("..").locator("..").locator("..")
    calshi_clarity_data = calshi_clarity_chart.locator(">div:nth-child(1)")
    image_path = FileUtils.get_path("images", "calshi_clarity.png")
    save_screenshot(calshi_clarity_chart, image_path)
    image_key = upload_image(client, image_path)
    logger.info(f"calshi clarity指标图: {image_path}, {image_key}")

    # 获取calshi clarity预测趋势图数据
    calshi_clarity_data_text = calshi_clarity_data.inner_text().replace("\n", " ")
    logger.info(f"calshi_clarity_data_text: {calshi_clarity_data_text}")
    latest_data = f"calshi概率: {calshi_clarity_data_text}"
    
    page.close()
    return latest_data, image_key

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
    fetch_and_push_btc_info()

if __name__ == "__main__":
    main()