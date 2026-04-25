import os
from time import sleep
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
import requests
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page, Locator
from utils.file_utils import FileUtils
from loguru import logger
from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())


LOCAL_DEV = os.getenv("LOCAL_DEV") == "true"
PAGELOAD_TIMEOUT_MS = 60000 if not LOCAL_DEV else 10000


def list_pages(context: BrowserContext) -> None:
    pages = list(context.pages)
    logger.info(f"open pages: {len(pages)}")
    for i, page in enumerate(pages, start=1):
        try:
            logger.info(f"{i}. title={page.title()} url={page.url}")
        except Exception:
            logger.exception(f"{i}. failed to read page info")


def find_pages_by_title(context: BrowserContext, title_keyword: str) -> List[Dict[str, Any]]:
    keyword = title_keyword.lower()
    matches: List[Dict[str, Any]] = []
    for page in context.pages:
        try:
            page_title = page.title()
            if keyword in page_title.lower():
                matches.append({"page": page, "title": page_title, "url": page.url})
        except Exception:
            logger.exception("failed to read page title")
    return matches


def find_pages_by_url(context, url_keyword: str) -> List[Dict[str, Any]]:
    keyword = url_keyword.lower()
    matches: List[Dict[str, Any]] = []
    for page in context.pages:
        try:
            page_url = page.url
            if keyword in page_url.lower():
                matches.append({"page": page, "title": page.title(), "url": page_url})
        except Exception:
            logger.exception("failed to read page info")
    return matches


def open_page(context: BrowserContext, url: str, *, listener: Any = None):
    page = context.new_page()
    if listener:
        page.on("response", listener.handle_response)
    page.goto(url)
    page.bring_to_front()

    page.wait_for_load_state("domcontentloaded", timeout=PAGELOAD_TIMEOUT_MS)
    try:
        page.wait_for_load_state("networkidle", timeout=PAGELOAD_TIMEOUT_MS)
    except Exception:
        pass
    try:
        logger.info(f"page loaded: {page.title()}")
    except Exception:
        logger.info(f"page loaded: {page.url}")
    return page


def activate_page(
    context: BrowserContext,
    title_keyword: Optional[str] = None,
    url_keyword: Optional[str] = None,
    *,
    refresh: bool = False,
    new_url: Optional[str] = None,
    close_other_pages: bool = False,
):
    if not title_keyword and not url_keyword:
        logger.warning("activate_page called without title/url keyword")
        return None

    matches_by_title: List[Dict[str, Any]] = []
    matches_by_url: List[Dict[str, Any]] = []

    if title_keyword:
        matches_by_title = find_pages_by_title(context, title_keyword)
    if url_keyword:
        matches_by_url = find_pages_by_url(context, url_keyword)

    if title_keyword and url_keyword:
        title_urls = {p["url"] for p in matches_by_title}
        url_urls = {p["url"] for p in matches_by_url}
        common_urls = title_urls & url_urls
        matches = [p for p in matches_by_title if p["url"] in common_urls]
        if not matches:
            logger.warning(f"no page matched title={title_keyword} and url={url_keyword}")
            return None
    elif title_keyword:
        matches = matches_by_title
        if not matches:
            logger.warning(f"no page matched title={title_keyword}")
            return None
    else:
        matches = matches_by_url
        if not matches:
            logger.warning(f"no page matched url={url_keyword}")
            return None

    if close_other_pages and len(matches) > 1:
        for index, page_info in enumerate(matches):
            if index == 0:
                continue
            try:
                page_info["page"].close()
            except Exception:
                logger.exception(f"failed to close extra page: {page_info.get("url")}")

    page = matches[0]["page"]
    page.bring_to_front()
    logger.info(f"activated page: title={page.title()} url={page.url}")

    if refresh:
        try:
            page.reload()
            page.wait_for_load_state("domcontentloaded", timeout=PAGELOAD_TIMEOUT_MS)
            try:
                page.wait_for_load_state("networkidle", timeout=PAGELOAD_TIMEOUT_MS)
            except Exception:
                pass
            logger.info(f"page refreshed: {page.title()}")
        except Exception:
            logger.exception("page refresh failed")
            return None

    if new_url:
        page.goto(new_url)
        logger.info(f"navigated to: {new_url}")
        page.wait_for_load_state("domcontentloaded", timeout=PAGELOAD_TIMEOUT_MS)
        try:
            page.wait_for_load_state("networkidle", timeout=PAGELOAD_TIMEOUT_MS)
        except Exception:
            pass
        try:
            logger.info(f"page loaded: {page.title()}")
        except Exception:
            logger.exception(f"page loaded: {page.url}")
        return page

    return page


def scroll_to_bottom(page: Page) -> Optional[bool]:
    if not page:
        return None
    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
    page.wait_for_timeout(5000)
    logger.info("scrolled to bottom")
    return True


def scroll_by(page: Page, delta_y: int) -> bool:
    try:
        current_scroll = page.evaluate("window.pageYOffset || document.documentElement.scrollTop")
        new_scroll_position = current_scroll + delta_y
        new_scroll_position = max(0, new_scroll_position)
        max_scroll_height = page.evaluate(
            "Math.max(document.body.scrollHeight, document.documentElement.scrollHeight) - window.innerHeight"
        )
        new_scroll_position = min(new_scroll_position, max_scroll_height)
        page.evaluate(f"window.scrollTo(0, {new_scroll_position});")
        page.wait_for_timeout(2000)
        logger.info(
            "scrolled: from=%s to=%s delta=%s",
            current_scroll,
            new_scroll_position,
            delta_y,
        )
        return True
    except Exception:
        logger.exception("scroll failed")
        return False


def find_element(
    parent: Page | Locator,
    element_info: tuple[str, str],  # 元组：(名称, CSS选择器)
    *,
    timeout_ms: int = 10000,
    state: str = "visible"  # 可传 attached / hidden / detached
):
    try:
        ele_name, ele_selector = element_info
        logger.info(f"finding element: {ele_name} ({ele_selector})")
        element = parent.locator(ele_selector)
        element.wait_for(timeout=timeout_ms, state=state)
        # element = page.wait_for_selector(ele_selector, timeout=timeout_ms, state='visible')
        if element:
            logger.info(f"element found: {ele_name}, state={state}")
            return element
        logger.info(f"element not found: {element_info}")
        return None
    except Exception:
        logger.exception(f"find element failed: {element_info}")
        return None

def save_screenshot(element: Locator, path: str):
    if not element:
        logger.error("element is None")
        return
    try:
        # 调用 screenshot 方法
        element.screenshot(path=path)
        logger.info(f"✅ 截图成功！已保存为: {path}")
        # (可选) 你可以在可视化的浏览器中看到元素被“闪烁”一下，那是 Playwright 在聚焦它
        
    except Exception as e:
        logger.error(f"❌ 截图失败: {e}")
        # 常见失败原因：元素不存在、元素是隐藏的(width/height为0)

def _to_absolute_url(page: Page, url: Optional[str]) -> Optional[str]:
    if not url:
        return url
    if url.startswith(("http://", "https://", "data:", "blob:")):
        return url

    page_url = page.url
    if url.startswith("/"):
        parsed = urlparse(page_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        absolute_url = base_url + url
        logger.info("absolute url (root): %s -> %s", url, absolute_url)
        return absolute_url

    absolute_url = urljoin(page_url, url)
    logger.info("absolute url (join): %s -> %s", url, absolute_url)
    return absolute_url

def perform_action(
    page: Page,
    element_info: tuple[str, str],  # 元组：(名称, CSS选择器)
    *,
    timeout_ms: int = 10000,
    state: str = "visible",  # 可传 attached / hidden / detached
    action: str = "click",
    value: Optional[str] = None,
    download_path: Optional[str] = None,
):
    try:
        ele_name, _ = element_info
        element = find_element(page, element_info, timeout_ms=timeout_ms, state=state)
        if not element:
            return None

        logger.info(f"action={action} element={ele_name} state={state}")

        if action == "click":
            element.hover()
            sleep(0.5)
            element.click()
            logger.info(f"clicked: {ele_name}")
            return True

        if action == "click_only":
            element.click()
            logger.info(f"clicked: {ele_name}")
            return True

        if action == "get_text":
            text_value = element.text_content()
            logger.info(f"text: {text_value}")
            return text_value

        if action == "get_inner_text":
            text_value = element.inner_text()
            logger.info(f"inner text: {text_value}")
            return text_value

        if action == "get_inner_html":
            html_value = element.inner_html()
            preview = html_value[:100] + "..." if html_value and len(html_value) > 100 else html_value
            logger.info(f"inner html: {preview}")
            return html_value

        if action == "get_attribute":
            if not value:
                logger.warning("get_attribute requires value=<attr_name>")
                return None
            attr_value = element.get_attribute(value)
            logger.info(f"attribute {value}={attr_value}")
            return attr_value

        if action == "input_text":
            if value is None:
                logger.warning("input_text requires value=<text>")
                return False
            element.fill(value)
            logger.info(f"filled text: {value}")
            return True

        if action == "clear_input":
            element.fill("")
            logger.info(f"cleared input: {ele_name}")
            return True

        if action == "get_image":
            tag_name = element.evaluate("el => el.tagName.toLowerCase()")
            if tag_name != "img":
                logger.warning(f"not img element: {tag_name}")
                return None

            img_src = element.get_attribute("src")
            if not img_src:
                logger.warning("img has no src")
                return None
            img_src = _to_absolute_url(page, img_src)
            logger.info(f"image url: {img_src}")

            if download_path:
                try:
                    os.makedirs(os.path.dirname(download_path), exist_ok=True)
                    response = requests.get(img_src, timeout=30)
                    response.raise_for_status()
                    with open(download_path, "wb") as f:
                        f.write(response.content)
                    logger.info(f"image downloaded: {download_path}")
                    return download_path
                except Exception:
                    logger.exception(f"image download failed")
                    return img_src
            return img_src

        if action == "get_image_screenshot":
            tag_name = element.evaluate("el => el.tagName.toLowerCase()")
            if tag_name != "img":
                logger.warning(f"not img element: {tag_name}")
                return None

            if download_path:
                try:
                    os.makedirs(os.path.dirname(download_path), exist_ok=True)
                    # element.wait_for_element_state("stable")
                    element.screenshot(path=download_path)
                    logger.info(f"image screenshot saved: {download_path}")
                    return download_path
                except Exception:
                    logger.exception(f"image screenshot failed: {download_path}")
                    img_src = element.get_attribute("src")
                    if img_src:
                        img_src = _to_absolute_url(page, img_src)
                        logger.info(f"fallback image url: {img_src}")
                        return img_src
                    return None

            img_src = element.get_attribute("src")
            if not img_src:
                logger.warning("img has no src")
                return None
            img_src = _to_absolute_url(page, img_src)
            logger.info(f"image url: {img_src}")
            return img_src

        if action == "hover":
            element.hover()
            logger.info(f"hovered: {ele_name}")
            return True

        if action == "double_click":
            element.dblclick()
            logger.info(f"double clicked: {ele_name}")
            return True

        if action == "right_click":
            element.click(button="right")
            logger.info(f"right clicked: {ele_name}")
            return True

        if action == "scroll_into_view":
            element.scroll_into_view_if_needed()
            logger.info(f"scrolled into view: {ele_name}")
            return True

        if action == "is_visible":
            result = element.is_visible()
            logger.info(f"is visible={result}")
            return result

        if action == "is_enabled":
            result = element.is_enabled()
            logger.info(f"is enabled={result}")
            return result

        logger.warning(f"unsupported action: {action}")
        return None
    except Exception:
        logger.exception(f"perform_action failed: {ele_name}")
        return None


if __name__ == "__main__":
    with sync_playwright() as p:
        p: Playwright
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        url = 'https://www.coinglass.com/zh/pro/i/ahr999'
        page = open_page(context, url)
        element = find_element(page, ("ahr999指标图", "canvas"))
        shot_path = FileUtils.get_path("images", "canvas.png")
        save_screenshot(element, shot_path)
        page.close()
