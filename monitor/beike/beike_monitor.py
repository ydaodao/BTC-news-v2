from warnings import deprecated
from time import sleep
from utils.file_utils import FileUtils
from utils.collection_utils import CollectionUtils
from playwright.sync_api import sync_playwright, Playwright
from utils.playwright_utils import open_page, find_pages_by_url, find_element, human_click, random_sleep, human_move
from feishu.robot_service import MsgBotService
from utils.date_utils import DateUtils
from loguru import logger
from urllib.parse import urlparse, parse_qs

class BeikeNetworkListener:
    def __init__(self):
        self.all_house_list = []

    def handle_response(self, response):
        url = response.url
        parsed = urlparse(response.request.url)
        # 示例：{'cityId': ['110000'], 'dataSource': ['ZF'], 'curPage': ['1'], 'condition': ['Urt200600000001Uin1Uie1l3l4l5oerp12100Urt200600000001Uin1Uie1l3l4l5oerp12500Urco32'], 'maxLatitude': ['40.01991395430792'], 'minLatitude': ['39.98766483351737'], 'maxLongitude': ['116.44363300187156'], 'minLongitude': ['116.36354008260193']}
        params = parse_qs(parsed.query)
        # 房源列表接口
        if "proxyApi/i.c-pc-webapi.ke.com/map/houselist" in url and "Urco32" in params.get("condition", [])[0]:
            try:
                data = response.json()
                house_list = data.get("data", {}).get("list", [])
                logger.info(f"Page {params.get('curPage', [])[0]} 解析到{len(house_list)}条房源")
                self.all_house_list.extend(house_list)

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
    
    def send_general_card(self, new_house_list):
        logger.info(f"构建房源发送卡片")
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
                area = 0

            # 避免越界
            room = parts[1].strip() if len(parts) > 1 else ""
            direction = parts[2].strip() if len(parts) > 2 else ""
            tag = parts[3].strip() if len(parts) > 3 else ""
            return int(area), room, direction, tag

        template_variable = {"card_title": f'{DateUtils.now_str(fmt="%m.%d")} 房源更新', "list": []}
        # new_house_list 排序，按面积从大到小排序
        new_house_list.sort(key=lambda x: parse_desc(x["desc"])[0], reverse=True)
        for i, item in enumerate(new_house_list):
            area, room, direction, tag = parse_desc(item["desc"])
            if area < 110 or "南" not in direction:
                continue
            price = parse_price(item["priceStr"])
            other_price = int(price * 0.1)
            other_price_str = f"【含服务费{other_price}】" if tag == "贝壳优选" else ""

            template_variable["list"].append({
                "title": f"{i+1}、{direction}，{area}m²，{price + other_price}元/月，{item['title']}{other_price_str}",
                "title_url": item["actionUrl"]
            })
        
        logger.info(f"过滤后新增{len(template_variable['list'])}条房源")
        if len(template_variable["list"]) == 0:
            return
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

            @deprecated("use change_price_range instead")
            def select_fangxing():
                # 房型选择
                fangxing = find_element(page, ("房型选择", "ul.filter li:nth-child(3)"))
                human_click(fangxing)
                fangxing_5 = page.locator("ul.filter-item li").filter(has_text="五室及以上")
                human_click(fangxing_5)
                # 检查五室选中状态
                fangxing_5_class = fangxing_5.locator("label span:nth-child(1)").get_attribute("class")
                fangxing_5_check = "ant-checkbox-checked" in str(fangxing_5_class)
                # 点击确定按钮
                confirm = page.locator(".save._color").filter(has_text="确定")
                human_click(confirm)
                return fangxing_5_check
            
            def change_price_range(oerp: str):
                # 价格范围选择
                price_range = find_element(page, ("价格范围选择", "ul.filter li:nth-child(2)"))
                human_click(price_range)
                oerp_input = page.locator("input[name='oerp']")
                oerp_input.fill(oerp)
                random_sleep()
                # 点击确定按钮
                confirm = page.locator(".save._color").filter(has_text="确定")
                human_click(confirm)
                
            # 按面积排序
            def change_area_sort():
                logger.info("按面积降序排序")
                area = page.locator("li").filter(has_text="面积")
                human_click(area)
                area_flag = area.locator("i").get_attribute("class")
                if area_flag == "orderImgUP":
                    human_click(area)
                else:
                    human_click(area)
                    human_click(area)

            # 滚动获取更多房源信息
            def scroll_to_get_new_house_list():
                """滚动到最新房源列表"""
                base_locator = page.locator(".house-card ul > li:nth-child(1)")
                human_move(page, base_locator)
                page.mouse.wheel(0, 100)
                page.wait_for_timeout(1000)
                page.mouse.wheel(0, 100)
                page.wait_for_timeout(3000)
                # 回到初始位置
                base_locator.scroll_into_view_if_needed()

            change_price_range("12100")
            change_price_range("12500")
            change_area_sort()
            page.wait_for_timeout(5000)
            scroll_to_get_new_house_list()

            listener.all_house_list = CollectionUtils.unique_by_key(listener.all_house_list, "actionUrl")
            new_house_list, _ = listener.check_house_diff(listener.all_house_list)
            # 发送房源更新卡片
            listener.send_general_card(new_house_list)
            # 更新最新房源信息
            listener.update_house_info(listener.all_house_list)

            # page.wait_for_timeout(50000)  # 等待很久，但不阻塞事件循环
        

if __name__ == "__main__":
    begin_crawler()