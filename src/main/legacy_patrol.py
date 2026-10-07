# -*- coding: utf-8 -*-
"""旧版巡逻统计模块（2526 赛季遗留）—— Q7：昨天还能跑。

背景：本模块从上一届的巡逻系统原样迁移，上周还"能跑"。
最近的两次提交（见 git log）之后 CI 依旧全绿，但验收脚本报出的
数字不对，有的调用甚至卡死。上级只留了一句：昨天还能跑。

任务（题面 Q7·修复任务与提交物）：
1. 本模块共埋有 6 处 bug，其中两对互相遮蔽——修好 A 才会暴露 B；
2. 修复全部 6 处（验收以各函数 docstring 的契约为准，隐藏测试逐条核对）；
3. 在你的 README 里逐条写明：错在哪、你是怎么定位到的。

提示：不要迷信 git log 里的"修复"——有一件事被越修越错了。
"""

# ---------------------------------------------------------------------------
# 路线统计
# ---------------------------------------------------------------------------


def segment_length_cm(p1, p2):
    """两个检查点 (x, y) 之间的路线长度，单位：厘米。
    检查点坐标单位为格，1 格 = 1 米 = 100 厘米，路线按曼哈顿距离计算。"""
    return (abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])) * 100


def total_route_meters(points):
    """整条巡逻路线的长度，单位：米。
    points 为检查点序列 [(x, y), ...]，至少两个点。"""
    distance_in_meters = 0
    for i in range(len(points) - 1):
        distance_in_meters += segment_length_cm(points[i], points[i + 1])
    return distance_in_meters


# ---------------------------------------------------------------------------
# 事件日志
# ---------------------------------------------------------------------------
def parse_event(line):
    """解析一行事件日志，形如 "MOVE,3" / "SCAN,0" / "IDLE,1"。
    合法返回 {"type": str, "count": int}；脏行返回 None（不得抛异常）。"""
    parts = line.strip().split(",")
    if len(parts) != 2 or parts[0] not in ("MOVE", "SCAN", "IDLE"):
        return None
    if not parts[1].isdigit():
        return None
    return {"type": parts[0], "count": int(parts[1])}


def first_positive(samples):
    """返回样本序列中第一个正数；若没有正数，返回 None（上游约定）。"""
    for s in samples:
        if s > 0:
            return s
    return None


def calibrate(samples):
    """以第一个正样本为基线计算累计漂移：sum(s - baseline)。
    样本为空或没有正样本时，漂移为 0。"""
    baseline = first_positive(samples)
    drift = 0
    for s in samples:
        drift += s - baseline
    return drift


def summarize_events(events, max_id):
    """统计 id 不超过 max_id 的事件。

    events: [{"id": int, "move": int, "samples": [int, ...]}, ...]
    每个事件的步数贡献 = move + calibrate(samples)。
    返回 {"events": 统计到的事件数, "steps": 步数总和}。
    """
    used = 0
    steps = 0
    for e in events:
        if e["id"] < max_id:
            used += 1
            steps += e["move"] + calibrate(e["samples"])
    return {"events": used, "steps": steps}


def log(message, history=[]):
    """向历史追加一条日志并返回整个历史列表。
    不显式传入 history 时，每次调用都从空历史开始。"""
    history.append(message)
    return history


# ---------------------------------------------------------------------------
# 旧版巡逻模拟
# ---------------------------------------------------------------------------
def run_legacy_sim(rounds, stamina_start=100):
    """旧版巡逻模拟。

    契约（验收以本条为准）：
    - 依次执行第 0 .. rounds-1 轮，每轮基础消耗 8 点体力；
    - 第 4 轮起（轮号 >= 3）每轮额外消耗 5 点；
    - 任一轮结束后体力 <= 20 时立即终止，不再继续后面的轮；
    - trace 记录 (轮号, 该轮结束时的体力)；
    - 返回 {"rounds": 已执行轮数, "stamina": 剩余体力, "trace": trace}。
    """
    stamina = stamina_start
    round_ = 0
    trace = []
    while round_ < rounds:
        stamina -= 8
        if round_ >= 3:
            stamina -= 5
        trace.append((round_, stamina))
        if stamina > 20:
            break
    return {"rounds": len(trace), "stamina": stamina, "trace": trace}
