"""指标权重管理"""

# 初始权重（根据设计文档）
DEFAULT_WEIGHTS = {
    "tips_10y": 0.28,
    "dxy": 0.23,
    "spdr": 0.17,
    "cot": 0.15,
    "premium": 0.17,
}

WEIGHT_LIMITS = {
    "min": 0.05,
    "max": 0.40,
}


def get_weights() -> dict:
    """获取当前权重。后续可从rule_scores表读取最新权重。"""
    return DEFAULT_WEIGHTS.copy()


def adapt_weights(accuracy_map: dict[str, float]) -> dict:
    """根据各指标方向准确率动态调整权重。

    Args:
        accuracy_map: {"tips_10y": 0.72, "dxy": 0.65, ...}

    Returns:
        调整后的权重字典
    """
    current = get_weights()
    adjustments = {}

    avg_acc = sum(accuracy_map.values()) / len(accuracy_map) if accuracy_map else 0.5

    for key, current_w in current.items():
        acc = accuracy_map.get(key, avg_acc)
        if acc > avg_acc + 0.05:
            adjustments[key] = current_w + 0.02
        elif acc < avg_acc - 0.05:
            adjustments[key] = current_w - 0.02
        else:
            adjustments[key] = current_w

    # Clamp权重
    for key in adjustments:
        adjustments[key] = max(WEIGHT_LIMITS["min"], min(WEIGHT_LIMITS["max"], adjustments[key]))

    # 归一化到100%
    total = sum(adjustments.values())
    for key in adjustments:
        adjustments[key] = round(adjustments[key] / total, 4)

    return adjustments
