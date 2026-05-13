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
                for item in house_list:
                    # 移除标签字段，没啥意义
                    item.pop("tags", "")
                    # 解析价格
                    item["price"] = self._parse_price(item["priceStr"])
                    # 解析面积、房型、朝向、标签
                    area, room, direction, source = self._parse_desc(item["desc"])
                    item["area"] = area
                    item["room"] = room
                    item["direction"] = direction
                    item["source"] = source
                
                self.all_house_list.extend(house_list)
                # 去重
                self.all_house_list = CollectionUtils.unique_by_key(self.all_house_list, "actionUrl")
                # 排序
                self.all_house_list.sort(key=lambda x: x["area"], reverse=True)
            except Exception as e:
                logger.error(f"解析房源失败: {e}")

    def _parse_price(self, price_str: str):
        if not price_str:
            return 0
        try:
            return int(price_str.replace("元/月", ""))
        except:
            return 0
    
    def _parse_desc(self, desc_str: str):
        # 从 "desc": "180m²|4室1厅2卫|东南|贝壳优选" 解析面积、房型、朝向、标签
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

    def update_house_info(self, house_list):
        path = FileUtils.get_path("monitor", "beike", "beike_house_list.json")
        FileUtils.write_json(path, house_list)

    # 基于item["actionUrl"]对比上次缓存：返回新增房源 + 封面图/价格发生变化的房源列表
    def check_house_diff(self, new_house_list):
        old_house_path = FileUtils.get_path("monitor", "beike", "beike_house_list.json")
        old_house_list = FileUtils.read_json(old_house_path) or []
        ignore_house_path = FileUtils.get_path("monitor", "beike", "ignore_house_list.json")
        ignore_house_list = FileUtils.read_json(ignore_house_path) or []

        logger.info(f"过滤前有 {len(new_house_list)} 条新房源")
        # ignore_house_list 中的内容是：1、南 北，267m²，12000元/月，整租·景龙国际 3室2厅。但 item.get("title") 可能是 整租·景龙国际 3室2厅。
        new_house_list = [
            item for item in new_house_list 
            if not any(item.get("title", "") in ignore_title for ignore_title in ignore_house_list)
        ]
        logger.info(f"过滤后有 {len(new_house_list)} 条新房源")
        
        # 获取老的房源信息
        old_house_map = {item.get("actionUrl"): item for item in old_house_list if item.get("actionUrl")}

        diff_house_list = []
        for item in new_house_list:
            action_url = item.get("actionUrl")
            if not action_url:
                continue

            old_item = old_house_map.get(action_url)
            if old_item is None:
                item["change_type"] = "新增"
                diff_house_list.append(item)
                continue

            if str(old_item.get("coverPic", "")) != str(item.get("coverPic", "")):
                item["change_type"] = "封面变更"
                diff_house_list.append(item)
                continue

            if old_item.get("price") != item.get("price"):
                item["change_type"] = f"价格变更{item.get("price") - old_item.get("price")}元"
                diff_house_list.append(item)
                continue

        return diff_house_list
    
    def send_house_list_card(self):
        diff_house_list = self.check_house_diff(self.all_house_list)

        logger.info(f"构建房源发送卡片")
        template_variable = {"card_title": f'{DateUtils.now_str(fmt="%m.%d")} 房源更新', "list": []}
        for i, item in enumerate(diff_house_list):
            area, room, direction, source = item["area"], item["room"], item["direction"], item["source"]
            if area < 130 or "南" not in direction or "公寓" in item["title"]:
                continue
            price = item["price"]
            other_price = int(price * 0.1)
            other_price_str = f"+【服务费{other_price}】" if source == "贝壳优选" else ""

            template_variable["list"].append({
                "title": f"{i+1}、{item['change_type']}，{direction}，{area}m²，{price}{other_price_str}元/月，{item['title']}",
                "title_url": item["actionUrl"],
                "desc": f"{item['title']}"
            })
        
        logger.info(f"过滤后新增{len(template_variable['list'])}条房源")
        if len(template_variable["list"]) == 0:
            return
        bot = MsgBotService()
        bot.send_general_card(template_variable=template_variable)

    def send_card_login_status(self):
        template_variable = {"card_title": f'{DateUtils.now_str(fmt="%m.%d")} 贝壳登录失效'}

        logger.info(f"发送登录状态卡片：{template_variable}")
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
                logger.info("移动到第一个房源")
                human_move(page, base_locator)
                for _ in range(10):
                    last_locator = page.locator(".house-card ul > li:last-child")
                    last_locator.scroll_into_view_if_needed()
                    page.wait_for_timeout(2000)
                    logger.info(f"第{_+1}次滚动到最新房源")
                    page.mouse.wheel(0, -100)
                    page.wait_for_timeout(2000)
                    page.mouse.wheel(0, 100)
                    page.wait_for_timeout(2000)
                # 回到初始位置
                base_locator.scroll_into_view_if_needed()

            change_price_range("12100")
            # 判断是否登录失效
            if page.locator('#loginModel:visible').count() > 0:
                listener.send_card_login_status()
                continue
            change_price_range("12500")
            change_area_sort()
            page.wait_for_timeout(5000)
            scroll_to_get_new_house_list()

            # 发送房源更新卡片
            listener.send_house_list_card()
            # 更新最新房源信息
            listener.update_house_info(listener.all_house_list)
            # page.wait_for_timeout(50000)  # 等待很久，但不阻塞事件循环
        

if __name__ == "__main__":
    begin_crawler()
