from datetime import datetime, timedelta, timezone
from typing import Union, Optional
import re

class DateUtils:
    """
    通用日期处理工具类
    所有时间默认处理为东八区（北京时间）
    """

    # --- 常量定义 ---
    TZ_UTC = timezone.utc
    TZ_CN = timezone(timedelta(hours=8))
    FMT_STD = "%Y-%m-%d %H:%M:%S"
    FMT_DATE = "%Y-%m-%d"
    FMT_TIME = "%H:%M:%S"

    # --- 1. 转换：时间戳 -> 日期对象/字符串 ---

    @staticmethod
    def timestamp_to_datetime(timestamp: Union[int, float, str], unit: str = "s") -> datetime:
        """
        将 Unix 时间戳转换为 datetime 对象 (东八区)
        :param timestamp: 时间戳 (int/float/str)
        :param unit: 单位 's' (秒) 或 'ms' (毫秒)
        """
        if isinstance(timestamp, str):
            timestamp = float(timestamp)
        
        # 处理毫秒
        if unit == "ms" or (isinstance(timestamp, float) and timestamp > 1e11):
            timestamp = timestamp / 1000.0

        # 核心逻辑：先转 UTC，再转东八区，避免本地环境时区干扰
        dt_utc = datetime.fromtimestamp(timestamp, tz=DateUtils.TZ_UTC)
        return dt_utc.astimezone(DateUtils.TZ_CN)

    @staticmethod
    def timestamp_to_str(timestamp: Union[int, float], fmt: str = FMT_STD, unit: str = "s") -> str:
        """将时间戳直接转换为格式化字符串"""
        dt = DateUtils.timestamp_to_datetime(timestamp, unit)
        return dt.strftime(fmt)

    # --- 2. 转换：字符串 -> 日期对象/时间戳 ---

    @staticmethod
    def str_to_datetime(date_str: str, fmt: str = FMT_STD) -> datetime:
        """
        将字符串解析为 datetime 对象
        :param date_str: 时间字符串
        :param fmt: 格式，默认 %Y-%m-%d %H:%M:%S
        """
        dt = datetime.strptime(date_str, fmt)
        # 如果字符串不含时区信息，默认将其视为东八区
        return dt.replace(tzinfo=DateUtils.TZ_CN)

    @staticmethod
    def str_to_timestamp(date_str: str, fmt: str = FMT_STD, unit: str = "s") -> Union[int, float]:
        """将字符串解析为 Unix 时间戳"""
        dt = DateUtils.str_to_datetime(date_str, fmt)
        return dt.timestamp() if unit == "s" else dt.timestamp() * 1000
    
    # -- 转换：datetime转字符串 --

    @staticmethod
    def datetime_to_str(dt: datetime, fmt: str = FMT_STD) -> str:
        """将 datetime 对象格式化为字符串"""
        return dt.strftime(fmt)

    # -- 转换：字符串转字符串 --
    @staticmethod
    def str_to_str(date_str: str, from_fmt: str = FMT_STD, to_fmt: str = FMT_STD) -> str:
        """将日期字符串格式化为另一个日期字符串"""
        dt = DateUtils.str_to_datetime(date_str, from_fmt)
        return DateUtils.datetime_to_str(dt, to_fmt)




    # --- 3. 爬虫专用：相对时间解析 ---

    @staticmethod
    def parse_relative_time(text: str, base_time: Optional[datetime] = None) -> datetime:
        """
        解析相对时间（如 "3分钟前", "2小时前", "昨天", "2天前"）
        常用于抖音、微博等爬虫数据清洗
        :param text: 相对时间字符串
        :param base_time: 基准时间（默认为当前时间）
        """
        if not base_time:
            base_time = datetime.now(DateUtils.TZ_CN)

        text = text.strip().lower()

        # 匹配 "刚刚"
        if "刚刚" in text or "just" in text:
            return base_time

        # 匹配 "x秒前"
        match = re.search(r"(\d+)\s*秒", text)
        if match:
            return base_time - timedelta(seconds=int(match.group(1)))

        # 匹配 "x分钟前"
        match = re.search(r"(\d+)\s*分", text)
        if match:
            return base_time - timedelta(minutes=int(match.group(1)))

        # 匹配 "x小时前"
        match = re.search(r"(\d+)\s*小时", text)
        if match:
            return base_time - timedelta(hours=int(match.group(1)))

        # 匹配 "x天前"
        match = re.search(r"(\d+)\s*天", text)
        if match:
            return base_time - timedelta(days=int(match.group(1)))

        # 匹配 "昨天"
        if "昨天" in text or "yesterday" in text:
            return base_time - timedelta(days=1)
        
        # 匹配 "前天"
        if "前天" in text:
            return base_time - timedelta(days=2)

        # 如果都不匹配，尝试直接解析为标准日期字符串
        try:
            return DateUtils.str_to_datetime(text)
        except ValueError:
            raise ValueError(f"无法解析的相对时间格式: {text}")

    # --- 4. 计算与差值 ---

    @staticmethod
    def get_diff(dt1: datetime, dt2: datetime, unit: str = "seconds") -> Union[int, float]:
        """
        计算两个时间的差值 (dt1 - dt2)
        :param unit: 'seconds', 'minutes', 'hours', 'days'
        """
        # 确保两个时间都有时区信息，否则强制设为东八区
        if dt1.tzinfo is None: dt1 = dt1.replace(tzinfo=DateUtils.TZ_CN)
        if dt2.tzinfo is None: dt2 = dt2.replace(tzinfo=DateUtils.TZ_CN)

        delta = dt1 - dt2
        total_seconds = delta.total_seconds()

        if unit == "seconds": return int(total_seconds)
        if unit == "minutes": return int(total_seconds / 60)
        if unit == "hours": return int(total_seconds / 3600)
        if unit == "days": return int(total_seconds / 86400)
        return total_seconds

    @staticmethod
    def now_str(fmt: str = FMT_STD) -> str:
        """获取当前时间的字符串"""
        return datetime.now(DateUtils.TZ_CN).strftime(fmt)

    @staticmethod
    def now_timestamp(unit: str = "s") -> Union[int, float]:
        """获取当前时间戳"""
        ts = datetime.now(DateUtils.TZ_CN).timestamp()
        return ts if unit == "s" else ts * 1000

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 时间戳转字符串 (模拟抖音数据)
    ts = 1710234567
    print(f"时间戳 -> 字符串: {DateUtils.timestamp_to_str(ts)}")

    # 2. 字符串转时间戳
    ts_back = DateUtils.str_to_timestamp("2024-03-12 10:00:00")
    print(f"字符串 -> 时间戳: {ts_back}")

    # 3. 解析爬虫常见的相对时间
    relative_dt = DateUtils.parse_relative_time("35分钟前")
    print(f"相对时间解析: {relative_dt}")

    # 4. 计算时间差
    now = datetime.now(DateUtils.TZ_CN)
    past = now - timedelta(hours=5)
    diff = DateUtils.get_diff(now, past, unit="hours")
    print(f"时间差计算: {diff} 小时")