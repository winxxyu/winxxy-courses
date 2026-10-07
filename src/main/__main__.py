# -*- coding: utf-8 -*-
"""`python main.py` 演示入口（不进测试，仅为了让你"看见"机器人动起来）。

逐步实现 TODO 后，这里会依次亮起更多环节：
  Q1 → 自检报告；Q3 → 载体机动演示；Q6 → 完整巡逻动画。
"""
import time

from . import (Facing, SentryGrid, hp_ratio, render_frame,
               status_report)


DEMO_OBSTACLES = [(2, 2), (3, 2), (4, 2), (2, 3), (2, 4), (6, 5), (6, 6)]


def banner(title):
    print("\n" + "=" * 46)
    print(title)
    print("=" * 46)


def demo_q1():
    banner("Q1 机器人自检")
    try:
        print(status_report("Sentry-07", "HERO", 65, 100, 20))
        print(status_report("Sentry-03", "INFANTRY", -5, 400, 79))
        print("hp_ratio(2, 3) =", hp_ratio(2, 3))
    except NotImplementedError:
        print("[Q1 尚未实现] 完成后这里会打印两行自检报告。")


def demo_q3():
    banner("Q3 载体机动演示（撞墙 → 转向 → 前进）")
    grid = SentryGrid(9, 8, DEMO_OBSTACLES, (8, 7))
    trail = set()
    script = [
        ("turn_right",), ("forward",), ("forward",), ("forward",),
        ("turn_right",), ("forward",), ("forward",),
        ("turn_left",), ("forward",), ("forward",), ("forward",),
    ]
    try:
        for op in script:
            trail.add(grid.current_pos)
            if op[0] == "turn_right":
                grid.turn_right()
            elif op[0] == "turn_left":
                grid.turn_left()
            else:
                grid.move_forward()
            print("\n".join(render_frame(grid, trail)))
            print("pos={} facing={} 撞击={} 电量={}".format(
                grid.current_pos, grid.facing.name,
                grid.collision_count, grid.fuel))
            time.sleep(0.25)
    except NotImplementedError:
        print("[Q3 的 TODO 尚未实现] 完成后这里会播放机动动画。")


def demo_q6():
    banner("Q6 巡逻任务演示")
    from . import run_patrol
    try:
        grid = SentryGrid(9, 8, DEMO_OBSTACLES, (8, 7), fuel=1000)
        stats = run_patrol(grid)
        print("巡逻结果：", stats)
    except NotImplementedError:
        print("[Q6 尚未实现] 完成后这里会跑完整巡逻并输出统计。")


def main():
    print(__doc__)
    demo_q1()
    demo_q3()
    demo_q6()
    banner("提示：python tools/run_seeds.py --q6 查看你在 200 张地图上的成绩")


if __name__ == "__main__":
    main()
