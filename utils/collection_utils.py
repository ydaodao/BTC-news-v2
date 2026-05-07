from typing import List, Dict, Any, Callable, Optional


class CollectionUtils:

    # =========================
    # list 去重（普通类型）
    # =========================

    @staticmethod
    def unique(arr: List[Any]) -> List[Any]:
        """
        普通数组去重
        保持顺序
        """
        return list(dict.fromkeys(arr))

    # =========================
    # dict 数组去重
    # =========================

    @staticmethod
    def unique_by_key(
        arr: List[Dict],
        key: str,
    ) -> List[Dict]:
        """
        根据指定 key 去重

        示例:
        unique_by_key(users, "id")
        """
        seen = set()
        result = []

        for item in arr:
            value = item.get(key)

            if value not in seen:
                seen.add(value)
                result.append(item)

        return result

    @staticmethod
    def unique_by_func(
        arr: List[Any],
        key_func: Callable,
    ) -> List[Any]:
        """
        根据函数去重

        示例:
        unique_by_func(users, lambda x: x["id"])
        """
        seen = set()
        result = []

        for item in arr:
            value = key_func(item)

            if value not in seen:
                seen.add(value)
                result.append(item)

        return result

    @staticmethod
    def unique_dict(arr: List[Dict]) -> List[Dict]:
        """
        dict 完全去重
        所有字段一致才算重复
        """
        seen = set()
        result = []

        for item in arr:
            marker = tuple(sorted(item.items()))

            if marker not in seen:
                seen.add(marker)
                result.append(item)

        return result

    # =========================
    # 查找
    # =========================

    @staticmethod
    def find_by_key(
        arr: List[Dict],
        key: str,
        value: Any,
    ) -> Optional[Dict]:
        """
        根据 key/value 查找
        """
        for item in arr:
            if item.get(key) == value:
                return item

        return None

    # =========================
    # 分组
    # =========================

    @staticmethod
    def group_by_key(
        arr: List[Dict],
        key: str,
    ) -> Dict[Any, List[Dict]]:
        """
        group by

        示例:
        group_by_key(users, "city")
        """
        result = {}

        for item in arr:
            group_key = item.get(key)

            if group_key not in result:
                result[group_key] = []

            result[group_key].append(item)

        return result


# ==========================================
# 使用示例
# ==========================================

if __name__ == "__main__":

    users = [
        {"id": 1, "name": "Tom", "age": 20},
        {"id": 2, "name": "Jack", "age": 18},
        {"id": 1, "name": "Tom", "age": 20},
    ]

    # 去重
    print("按 id 去重:")
    print(CollectionUtils.unique_by_key(users, "id"))

    # 完全去重
    print("完全去重:")
    print(CollectionUtils.unique_dict(users))

    # 查找
    print("查找 id=1:")
    print(CollectionUtils.find_by_key(users, "id", 1))

    # 分组
    print("按 age 分组:")
    print(CollectionUtils.group_by_key(users, "age"))

    # 普通数组
    arr = [1, 2, 2, 3, 3]

    print("普通去重:")
    print(CollectionUtils.unique(arr))