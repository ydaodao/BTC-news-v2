from datetime import datetime
import math
from datetime import timedelta
from time import sleep
import json
import yaml
from utils.file_utils import FileUtils
from playwright.sync_api import sync_playwright, Playwright
from utils.playwright_utils import open_page, find_pages_by_url, find_element, smart_click
from feishu.robot_service import MsgBotService
from utils.date_utils import DateUtils
from loguru import logger

class BeikeNetworkListener:
    def __init__(self):
        self.house_list = []
        self.house_list_decrease = False

    def handle_response(self, response):
        url = response.url

        # 房源列表接口
        if "proxyApi/i.c-pc-webapi.ke.com/map/houselist" in url and self.house_list_decrease:
            try:
                data = response.json()
                house_list = data.get("data", {}).get("list", [])
                logger.info(f"解析到{len(house_list)}条房源")

                new_house_list, old_house_list = self.check_house_diff(house_list)
                logger.info(f"新增{len(new_house_list)}条房源")
                logger.info(f"下架{len(old_house_list)}条房源")
                
                if len(new_house_list) > 0 or len(old_house_list) > 0:
                    # 发送房源更新卡片
                    self.send_general_card(new_house_list, old_house_list)

                # 更新最新房源信息
                self.update_house_info(house_list)
            except Exception as e:
                logger.error(f"解析房源失败: {e}")

    def update_house_info(self, house_list):
        path = FileUtils.get_path("monitor", "beike", "beike_house_list.json")
        FileUtils.write_json(path, house_list)

    # 检查新获取的房源list，跟存储的差异
    def check_house_diff(self, new_house_list):
        path = FileUtils.get_path("monitor", "beike", "beike_house_list.json")
        old_house_list = FileUtils.read_json(path) or []

        new_house_ids = set(item["actionUrl"] for item in new_house_list)
        old_house_ids = set(item["actionUrl"] for item in old_house_list)

        new_diff_house_ids = new_house_ids - old_house_ids
        old_diff_house_ids = old_house_ids - new_house_ids

        # 返回item列表
        new_house_list = [item for item in new_house_list if item["actionUrl"] in new_diff_house_ids]
        old_house_list = [item for item in old_house_list if item["actionUrl"] in old_diff_house_ids]

        return new_house_list, old_house_list
    
    def send_general_card(self, new_house_list, old_house_list):
        def parse_price(price_str: str):
            if not price_str:
                return 0
            try:
                return float(price_str.replace("元/月", ""))
            except:
                return 0

        # 从 "desc": "180m²|4室1厅2卫|东南|贝壳优选" 解析面积、房型、朝向、标签
        def parse_desc(desc_str: str):
            if not desc_str:
                return 0, "", "", ""
            parts = desc_str.split("|")
            area = parts[0].strip()
            if area.endswith("m²"):
                area = area[:-2]
            else:
                area = ""

            # 避免越界
            room = parts[1].strip() if len(parts) > 1 else ""
            direction = parts[2].strip() if len(parts) > 2 else ""
            tag = parts[3].strip() if len(parts) > 3 else ""
            return area, room, direction, tag

        # new_house_list 排序，按面积从大到小排序
        new_house_list.sort(key=lambda x: parse_desc(x["desc"])[0], reverse=True)
        # old_house_list 排序，按面积从大到小排序
        old_house_list.sort(key=lambda x: parse_desc(x["desc"])[0], reverse=True)

        template_variable = {"card_title": f'{DateUtils.now_str(fmt="%m.%d")} 房源更新', "list": []}
        for i, item in enumerate(new_house_list):
            area, room, direction, tag = parse_desc(item["desc"])
            price = parse_price(item["priceStr"])
            other_price_str = f"【服务费{int(price//10)}】" if tag == "贝壳优选" else ""

            template_variable["list"].append({
                "title": f"{i+1} 新增：{item['title']}，{area}m²，{item["priceStr"]}",
                "title_url": item["actionUrl"],
                "desc": f"{item['desc']}{other_price_str}"
            })
        
        for i, item in enumerate(old_house_list):
            area, room, direction, tag = parse_desc(item["desc"])
            price = parse_price(item["priceStr"])
            other_price_str = f"【服务费{int(price//10)}】" if tag == "贝壳优选" else ""
            template_variable["list"].append({
                "title": f"{i+1} 下架：{item['title']}，{area}m²，{item["priceStr"]}",
                "desc": f"{item['desc']}{other_price_str}"
            })

        bot = MsgBotService()
        bot.send_general_card(template_variable=template_variable)

def begin_crawler():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        pages = find_pages_by_url(context, "https://map.ke.com/map/110000/ZF")
        for page in pages:
            page.bring_to_front()
            listener = BeikeNetworkListener()
            page.on("response", listener.handle_response)
            logger.info("贝壳房源更新监控开始")

            def select_fangxing():
                # 房型选择
                fangxing = find_element(page, ("房型选择", "ul.filter li:nth-child(3)"))
                smart_click(fangxing)
                fangxing_5 = page.locator("ul.filter-item li").filter(has_text="五室及以上")
                smart_click(fangxing_5)
                # 检查五室选中状态
                fangxing_5_class = fangxing_5.locator("label span:nth-child(1)").get_attribute("class")
                fangxing_5_check = "ant-checkbox-checked" in str(fangxing_5_class)
                # 点击确定按钮
                confirm = page.locator(".save._color").filter(has_text="确定")
                smart_click(confirm)
                return fangxing_5_check
            
            # 按面积排序
            def change_area_sort():
                logger.info("按面积排序")
                area = page.locator("li").filter(has_text="面积")
                smart_click(area)
                area_flag = area.locator("i").get_attribute("class")
                if area_flag == "orderImgUP":
                    listener.house_list_decrease = True
                    smart_click(area)
                else:
                    smart_click(area)
                    listener.house_list_decrease = True
                    smart_click(area)


            if not select_fangxing():
                select_fangxing()
            change_area_sort()

            page.wait_for_timeout(50000)  # 等待很久，但不阻塞事件循环
        


if __name__ == "__main__":
    begin_crawler()