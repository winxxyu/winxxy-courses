# -*- coding: utf-8 -*-
"""Seed 批跑工具（维护者提供，学生可跑不可改——CI changed-files 白名单已排除 tools/）。

用法：
    python tools/run_seeds.py --q6                 # 200 seed 统计：成功率/碰撞/步数
    python tools/run_seeds.py --q6 --seed 47       # 单个 seed：地图 + 你自己的统计
    python tools/run_seeds.py --q6 --seed 47 --render  # 单 seed 逐步渲染（参考策略可视化）
    python tools/run_seeds.py --bonus              # Bonus 模式：BFS 正确性 + 排行榜
    python tools/run_seeds.py --q6 --seeds 50      # 只跑前 50 个 seed（快速迭代）

阈值（题面 Q6·验收阈值）：
    成功率 >= 92% ；平均碰撞 <= 1.5 ；成功案例 平均步数/BFS最短路 <= 1.35
"""
import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import main as M  # noqa: E402  学生的 src/main

SEED_COUNT = 200
FUEL = 1000  # 任务模式总电量（题面 Q6·任务模式参数）


# ---------------------------------------------------------------------------
# 地图生成器（确定性：同 seed 同地图。隐藏测试使用不同的 seed 区间）
# ---------------------------------------------------------------------------
def _reachable(width, height, obstacles, start, target):
    from collections import deque
    if start in obstacles or target in obstacles:
        return None
    queue = deque([start])
    seen = {start}
    while queue:
        x, y = queue.popleft()
        if (x, y) == target:
            return seen
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (0 <= nx < width and 0 <= ny < height
                    and (nx, ny) not in obstacles and (nx, ny) not in seen):
                seen.add((nx, ny))
                queue.append((nx, ny))
    return None


def make_map(seed):
    """seed → (width, height, obstacles, start, enemy)。保证 start→enemy 连通。"""
    import random
    rng = random.Random("cw2627-{}".format(seed))
    for _ in range(600):
        width = rng.randint(12, 20)
        height = rng.randint(12, 20)
        density = rng.uniform(0.10, 0.16)
        cells = [(x, y) for x in range(width) for y in range(height)]
        rng.shuffle(cells)
        keep = int(len(cells) * density)
        start = (0, 0)
        enemy = (width - 1, height - 1)
        obstacles = set(c for c in cells[:keep] if c not in (start, enemy))
        if _reachable(width, height, obstacles, start, enemy):
            return width, height, obstacles, start, enemy
    raise RuntimeError("seed {} 无法生成连通地图".format(seed))


def build_grid(seed):
    width, height, obstacles, start, enemy = make_map(seed)
    return M.SentryGrid(width, height, obstacles, enemy,
                        start_pos=start, fuel=FUEL)


def border_ring(width, height):
    ring = set()
    for x in range(-1, width + 1):
        ring.add((x, -1))
        ring.add((x, height))
    for y in range(-1, height + 1):
        ring.add((-1, y))
        ring.add((width, y))
    return ring


def bfs_len(start, target, obstacles):
    """工具内置 BFS（仅用于阈值测量。Bonus 要求你在 src/main 里自己实现）。"""
    from collections import deque
    obs = set(obstacles)
    if start == target:
        return 0
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        cur, d = queue.popleft()
        for nxt in ((cur[0] + 1, cur[1]), (cur[0] - 1, cur[1]),
                    (cur[0], cur[1] + 1), (cur[0], cur[1] - 1)):
            if nxt in obs or nxt in seen:
                continue
            if nxt == target:
                return d + 1
            seen.add(nxt)
            queue.append((nxt, d + 1))
    return -1


# ---------------------------------------------------------------------------
# 统计
# ---------------------------------------------------------------------------
def run_q6_stats(seed):
    stats = M.run_patrol(build_grid(seed))
    width, height, obstacles, start, enemy = make_map(seed)
    stats["_bfs"] = bfs_len(start, enemy, obstacles |
                            border_ring(width, height))
    return stats


def print_q6_report(all_stats):
    n = len(all_stats)
    succ = [s for s in all_stats if s["success"]]
    rate = len(succ) / n if n else 0
    avg_col = sum(s["collisions"] for s in all_stats) / n if n else 0
    ratios = [s["steps"] / s["_bfs"] for s in succ if s["_bfs"] > 0]
    avg_ratio = sum(ratios) / len(ratios) if ratios else float("nan")
    max_ratio = max(ratios) if ratios else float("nan")
    print("=" * 62)
    print("Q6 seed 统计（{} 张地图，电量 {}）".format(n, FUEL))
    print("=" * 62)
    print("成功率        {:6.1f}%   [阈值 >= 92%]   {}".format(
        rate * 100, "PASS" if rate >= 0.92 else "FAIL"))
    print("平均碰撞      {:6.2f}     [阈值 <= 1.5 ]   {}".format(
        avg_col, "PASS" if avg_col <= 1.5 else "FAIL"))
    print("步数/BFS 比   {:6.2f}     [阈值 <= 1.35]   {}  (max {})".format(
        avg_ratio, "PASS" if avg_ratio <= 1.35 else "FAIL",
        round(max_ratio, 2) if ratios else "-"))
    failed = [i + 1 for i, s in enumerate(all_stats) if not s["success"]]
    if failed:
        print("失败 seed（前 20 个）：{}".format(failed[:20]))
        print("复现：python tools/run_seeds.py --q6 --seed <N> --render")
    print("=" * 62)


def render_seed(seed, delay=0.12):
    """单 seed 逐步渲染。渲染循环用的是【参考策略】（贪心 + 沿墙脱困），
    用于观察死角形态；你的得分以你自己的 run_patrol 输出为准。"""
    grid = build_grid(seed)
    w, h, obs, start, enemy = make_map(seed)
    print("seed {}  地图 {}x{}  start={} enemy={} 障碍 {}".format(
        seed, w, h, start, enemy, len(obs)))
    trail = set()
    steps = 0
    wall = False
    hand = "L"
    wall_steps = 0
    entry = 0
    limit = w + h
    left_of = {M.Facing.UP: M.Facing.LEFT, M.Facing.LEFT: M.Facing.DOWN,
               M.Facing.DOWN: M.Facing.RIGHT, M.Facing.RIGHT: M.Facing.UP}
    right_of = {v: k for k, v in left_of.items()}

    def manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def has_candidate():
        pos = grid.current_pos
        dist = manhattan(pos, enemy)
        for f in (M.Facing.UP, M.Facing.DOWN, M.Facing.LEFT, M.Facing.RIGHT):
            d = f.delta
            nxt = (pos[0] + d[0], pos[1] + d[1])
            if not grid.is_blocked(*nxt) and manhattan(nxt, enemy) < dist:
                return True
        return False

    while steps < 500 and grid.fuel > 0 and not grid.found_enemy:
        pos = grid.current_pos
        if not has_candidate() and not wall:
            wall = True
            hand = "L"
            wall_steps = 0
            entry = manhattan(pos, enemy)
        if wall:
            side = left_of[grid.facing] if hand == "L" else right_of[grid.facing]
            opposite = right_of[grid.facing] if hand == "L" else left_of[grid.facing]

            def cell(f):
                d = f.delta
                return (pos[0] + d[0], pos[1] + d[1])

            if not grid.is_blocked(*cell(side)):
                grid.turn_left() if hand == "L" else grid.turn_right()
            elif grid.is_blocked(*cell(grid.facing)):
                if not grid.is_blocked(*cell(opposite)):
                    grid.turn_right() if hand == "L" else grid.turn_left()
                else:
                    grid.turn_right()
                    grid.turn_right()
        else:
            try:
                direction = M.next_step_toward(grid.current_pos, enemy,
                                               grid.obstacles, grid.facing)
            except NotImplementedError:
                print("next_step_toward（Q4）尚未实现，无法渲染贪心过程")
                return
            rights = {M.Facing.UP: 0, M.Facing.RIGHT: 1,
                      M.Facing.DOWN: 2, M.Facing.LEFT: 3}
            diff = (rights[direction] - rights[grid.facing]) % 4
            if diff == 3:
                grid.turn_left()
            else:
                for _ in range(diff):
                    grid.turn_right()
        grid.move_forward()
        steps += 1
        trail.add(pos)
        if wall:
            wall_steps += 1
            if wall_steps > limit and hand == "L":
                hand = "R"
                wall_steps = 0
            elif wall_steps > 2 * limit:
                wall = False
            elif has_candidate() and manhattan(grid.current_pos, enemy) < entry + 1:
                wall = False
        os.system("cls" if os.name == "nt" else "clear")
        print("seed {}  step {:>3}  pos {}  facing {:<5} 碰撞 {} 距离 {} {}".format(
            seed, steps, grid.current_pos, grid.facing.name,
            grid.collision_count, manhattan(grid.current_pos, enemy),
            "[沿墙脱困-{}]".format(hand) if wall else ""))
        print("\n".join(M.render_frame(grid, trail)))
        print("[参考策略渲染中…]" if not grid.found_enemy else "[到达敌方位置]")
        time.sleep(delay)
    print("参考策略结束：{}步 碰撞{} {}".format(
        steps, grid.collision_count,
        "成功" if grid.found_enemy else "未到达（观察卡死形态）"))
    print("你自己的实现：", end=" ")
    try:
        print(M.run_patrol(build_grid(seed)))
    except NotImplementedError:
        print("run_patrol 尚未实现")


# ---------------------------------------------------------------------------
# Bonus 模式
# ---------------------------------------------------------------------------
_BONUS_CASES = [
    (((0, 0), (5, 5), None), 10),
    (((2, 2), (2, 2), None), 0),
    (((0, 0), (1, 1), {(0, 1), (1, 0), (2, 1), (1, 2)}), -1),
]


def run_bonus():
    print("Bonus：bfs_path_length 正确性检查")
    ring = border_ring(6, 6)
    ok = True
    try:
        for (start, target, extra), expect in _BONUS_CASES:
            obs = ring | (extra or set())
            got = M.bfs_path_length(start, target, obs)
            mark = "ok" if got == expect else "X"
            print("  bfs{} → {} (期望 {}) [{}]".format(
                (start, target, "…" if extra is None else sorted(extra)),
                got, expect, mark))
            ok = ok and got == expect
    except NotImplementedError:
        print("  bfs_path_length 尚未实现——先完成 Bonus 再跑排行榜。")
        return
    if not ok:
        print("  BFS 有错误，先修复再上榜。")
        return
    print("BFS 正确，开始 200 seed 排行榜模式（BFS 导航）…")
    succ = 0
    total_steps = 0
    total_col = 0
    from collections import deque
    for i in range(1, SEED_COUNT + 1):
        w, h, obs, start, enemy = make_map(i)
        ringed = obs | border_ring(w, h)
        grid = M.SentryGrid(w, h, obs, enemy, start_pos=start, fuel=FUEL)
        steps = 0
        while steps < 500 and grid.fuel > 0 and not grid.found_enemy:
            pos = grid.current_pos
            best_f, best_len = None, None
            dx, dy = enemy[0] - pos[0], enemy[1] - pos[1]
            prefer_x = abs(dx) >= abs(dy)
            order = []
            for f in (M.Facing.RIGHT, M.Facing.LEFT, M.Facing.UP, M.Facing.DOWN):
                d = f.delta
                order.append((0 if ((d[0] != 0) == prefer_x) else 1, f))
            order.sort(key=lambda t: t[0])
            for _, f in order:
                d = f.delta
                nxt = (pos[0] + d[0], pos[1] + d[1])
                if nxt in obs:
                    continue
                length = M.bfs_path_length(nxt, enemy, ringed)
                if length >= 0 and (best_len is None or length < best_len):
                    best_f, best_len = f, length
            if best_f is None:
                break
            rights = {M.Facing.UP: 0, M.Facing.RIGHT: 1,
                      M.Facing.DOWN: 2, M.Facing.LEFT: 3}
            diff = (rights[best_f] - rights[grid.facing]) % 4
            if diff == 3:
                grid.turn_left()
            else:
                for _ in range(diff):
                    grid.turn_right()
            grid.move_forward()
            steps += 1
        if grid.found_enemy:
            succ += 1
        total_steps += steps
        total_col += grid.collision_count
    n = SEED_COUNT
    print("=" * 62)
    print("排行榜（本地单机版；战队名次以批改时 200 seed 重跑为准）")
    print("排名按 (成功率, 平均步数, 平均碰撞)")
    print("-" * 62)
    print("| {:<28} | {:>7} | {:>8} | {:>6} |".format(
        "你", "{:.1f}%".format(succ / n * 100),
        round(total_steps / n, 1), round(total_col / n, 2)))
    print("=" * 62)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Q6/Bonus seed 自测工具")
    ap.add_argument("--q6", action="store_true", help="跑 Q6 统计")
    ap.add_argument("--bonus", action="store_true", help="Bonus 排行榜模式")
    ap.add_argument("--seeds", type=int, default=SEED_COUNT,
                    help="seed 数量（默认 200）")
    ap.add_argument("--seed", type=int, default=None, help="只看某个 seed")
    ap.add_argument("--render", action="store_true", help="逐步渲染（配合 --seed）")
    args = ap.parse_args()

    if args.seed is not None:
        if args.render:
            render_seed(args.seed)
        else:
            w, h, obs, start, enemy = make_map(args.seed)
            grid = build_grid(args.seed)
            print("seed {} 地图 {}x{} 障碍 {}".format(args.seed, w, h, len(obs)))
            print("\n".join(M.render_frame(grid)))
            try:
                print("run_patrol →", M.run_patrol(grid))
            except NotImplementedError:
                print("run_patrol 尚未实现")
        return
    if args.bonus:
        run_bonus()
        return
    # 默认 --q6
    stats = []
    try:
        for i in range(1, args.seeds + 1):
            stats.append(run_q6_stats(i))
    except NotImplementedError as exc:
        print("尚未实现：{}（先完成对应 TODO 再跑统计）".format(exc))
        return
    print_q6_report(stats)


if __name__ == "__main__":
    main()
