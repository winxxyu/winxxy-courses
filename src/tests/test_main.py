# -*- coding: utf-8 -*-
"""可见测试 —— 你的规格书（鼓励先读测试再写实现）。

约定：对应函数还是 TODO（raise NotImplementedError）时自动 skip，
所以仓库刚到手 CI 就是绿的；实现一个函数，对应测试真正生效。
本地全绿 != 满分：条款细节与边界在批改方的隐藏测试里。
"""
import random

import pytest

import main as M
from main import Facing, SentryGrid, SentryState


def call(fn, *args, **kwargs):
    """调用学生函数；未实现则 skip 本条测试。"""
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        pytest.skip("对应 TODO 尚未实现")


# ---------------------------------------------------------------------------
# Q1 机器人自检
# ---------------------------------------------------------------------------
class TestQ1:
    def test_ratio_basic(self):
        assert call(M.hp_ratio, 65, 100) == 65
        assert call(M.hp_ratio, 0, 100) == 0
        assert call(M.hp_ratio, 100, 100) == 100

    def test_ratio_integer_result(self):
        got = call(M.hp_ratio, 150, 300)
        assert got == 50
        assert isinstance(got, int)

    def test_report_battery_tiers(self):
        # 三档：高电量 OK、中电量 WARNING、低电量 LOW
        assert call(M.status_report, "U", "HERO", 50, 100, 75).endswith("|OK")
        assert call(M.status_report, "U", "HERO", 50, 100, 30).endswith("|WARNING")
        assert call(M.status_report, "U", "HERO", 50, 100, 5).endswith("|LOW")

    def test_report_battery_ok(self):
        got = call(M.status_report, "Unit-1", "INFANTRY", 80, 100, 75)
        assert got == "Unit-1    | INFANTRY |HP  80%|BAT  75%|OK"


# ---------------------------------------------------------------------------
# Q2 战斗日志分析
# ---------------------------------------------------------------------------
class TestQ2:
    def test_sensor_lines(self):
        got = call(M.analyze_damage_log, ["F:32,L:5,R:12"])
        assert got["total"] == 49
        assert got["by_armor"] == {"front": 32, "left": 5, "right": 12}
        assert got["most_hit"] == "front"

    def test_json_lines(self):
        got = call(M.analyze_damage_log,
                   ['{"armor": "left", "damage": 40}'])
        assert got["total"] == 40
        assert got["most_hit"] == "left"
        assert got["avg"] == 40.0

    def test_mixed_with_dirt(self):
        got = call(M.analyze_damage_log, [
            "F:10",
            "# comment",
            "",
            "not a log line",
            '{"armor": "right", "damage": 15}',
        ])
        assert got["total"] == 25
        assert got["by_armor"] == {"front": 10, "left": 0, "right": 15}

    def test_json_id_dedup_counts_once(self):
        # 带 id 的 JSON 行：同一 id 只计第一次（题面规范 6）
        got = call(M.analyze_damage_log, [
            '{"armor": "front", "damage": 30, "id": 7}',
            '{"armor": "right", "damage": 50, "id": 7}',
        ])
        assert got["total"] == 30
        assert got["by_armor"] == {"front": 30, "left": 0, "right": 0}
        assert got["most_hit"] == "front"


    def test_empty_log(self):
        got = call(M.analyze_damage_log, [])
        assert got == {"total": 0,
                       "by_armor": {"front": 0, "left": 0, "right": 0},
                       "most_hit": None,
                       "avg": 0.0}


# ---------------------------------------------------------------------------
# Q3 SentryGrid
# ---------------------------------------------------------------------------
class TestQ3:
    def test_grid_construction(self):
        grid = SentryGrid(5, 5, [(2, 2)], (4, 4))
        assert grid.width == 5 and grid.height == 5
        assert grid.current_pos == (0, 0)
        assert grid.enemy_pos == (4, 4)
        assert grid.fuel == 100

    def test_setter_type_error(self):
        grid = SentryGrid(5, 5, [], (4, 4))
        try:
            call(grid.__class__.current_pos.fset, grid, (1, 2, 3))
        except TypeError:
            return
        pytest.fail("长度 != 2 应抛 TypeError")

    def test_move_forward(self):
        grid = SentryGrid(5, 5, [], (4, 4), start_pos=(1, 1),
                          facing=Facing.RIGHT)
        assert call(grid.move_forward) == (2, 1)
        assert grid.fuel == 99
        assert grid.collision_count == 0

    def test_move_into_obstacle(self):
        grid = SentryGrid(5, 5, [(2, 1)], (4, 4), start_pos=(1, 1),
                          facing=Facing.RIGHT)
        assert call(grid.move_forward) == (1, 1)      # 原地不动
        assert grid.collision_count == 1
        assert grid.facing is Facing.RIGHT            # 方向不变

    def test_turns(self):
        grid = SentryGrid(4, 4, [], (3, 3))
        assert call(grid.turn_left) is Facing.LEFT
        assert call(grid.turn_right) is Facing.UP
        assert call(grid.turn_right) is Facing.RIGHT


# ---------------------------------------------------------------------------
# Q4 贪心导航
# ---------------------------------------------------------------------------
class TestQ4:
    def test_straight_line(self):
        got = call(M.next_step_toward, (2, 2), (10, 2), set(), Facing.UP)
        assert got is Facing.RIGHT

    def test_larger_axis_first(self):
        got = call(M.next_step_toward, (2, 2), (4, 5), set(), Facing.LEFT)
        assert got is Facing.UP

    def test_blocked_falls_back_to_other_axis(self):
        got = call(M.next_step_toward, (2, 2), (5, 5), {(3, 2)}, Facing.DOWN)
        assert got is Facing.UP

    def test_no_candidate_returns_current_facing(self):
        got = call(M.next_step_toward, (0, 0), (0, 5), {(0, 1)}, Facing.LEFT)
        assert got is Facing.LEFT

    def test_random_open_field_always_reduces_distance(self):
        rng = random.Random(2026)
        for _ in range(20):
            pos = (rng.randint(0, 8), rng.randint(0, 8))
            target = (rng.randint(0, 8), rng.randint(0, 8))
            facing = rng.choice(list(Facing))
            got = call(M.next_step_toward, pos, target, set(), facing)
            if pos == target:
                assert got is facing
                continue
            nxt = (pos[0] + got.delta[0], pos[1] + got.delta[1])
            before = abs(pos[0] - target[0]) + abs(pos[1] - target[1])
            after = abs(nxt[0] - target[0]) + abs(nxt[1] - target[1])
            assert after < before


# ---------------------------------------------------------------------------
# Q5 哨兵决策机（主流程；条款细节见隐藏测试）
# ---------------------------------------------------------------------------
class TestQ5:
    def test_patrol_first_sight_goes_suspect(self):
        got = call(M.decide,
                   {"enemy_frames": (True,), "enemy_dist": 7,
                    "robot_type": "INFANTRY", "max_hp": 100},
                   SentryState.PATROL, 100, 0)
        assert got == ("SCAN", SentryState.SUSPECT)

    def test_suspect_two_frames_engage_and_shoot(self):
        got = call(M.decide,
                   {"enemy_frames": (True, True), "enemy_dist": 2,
                    "robot_type": "INFANTRY", "max_hp": 100},
                   SentryState.SUSPECT, 100, 0)
        assert got == ("SHOOT", SentryState.ENGAGE)

    def test_low_hp_retreats(self):
        got = call(M.decide,
                   {"enemy_frames": (True, True), "enemy_dist": 1,
                    "robot_type": "INFANTRY", "max_hp": 100},
                   SentryState.ENGAGE, 20, 0)
        assert got == ("RETREAT", SentryState.RETREAT)

    def test_recovered_returns_to_patrol(self):
        got = call(M.decide,
                   {"enemy_frames": (False,), "enemy_dist": None,
                    "robot_type": "INFANTRY", "max_hp": 100},
                   SentryState.RETREAT, 80, 0)
        assert got == ("RETURN", SentryState.RETURN)
        got = call(M.decide,
                   {"enemy_frames": (False,), "enemy_dist": None,
                    "robot_type": "INFANTRY", "max_hp": 100},
                   SentryState.RETURN, 80, 0)
        assert got == ("MOVE_BASE", SentryState.PATROL)

    def test_input_contract_violation_raises_value_error(self):
        with pytest.raises(ValueError):
            call(M.decide,
                 {"enemy_frames": (), "enemy_dist": 2,
                  "robot_type": "INFANTRY", "max_hp": 100},
                 SentryState.PATROL, 100, 0)
        with pytest.raises(ValueError):
            call(M.decide,
                 {"enemy_frames": (True,), "enemy_dist": 2,
                  "robot_type": "INFANTRY", "max_hp": 100},
                 "PATROL", 100, 0)

    def test_patrol_default_move(self):
        got = call(M.decide,
                   {"enemy_frames": (False, False), "enemy_dist": None,
                    "robot_type": "HERO", "max_hp": 100},
                   SentryState.PATROL, 100, 0)
        assert got == ("PATROL_MOVE", SentryState.PATROL)


# ---------------------------------------------------------------------------
# Q6 巡逻任务
# ---------------------------------------------------------------------------
class TestQ6:
    def test_small_obstacle_map_succeeds(self):
        obstacles = [(2, 2), (2, 3), (2, 4)]
        grid = SentryGrid(6, 6, obstacles, (5, 5), fuel=1000)
        got = call(M.run_patrol, grid)
        assert got["success"] is True
        assert got["collisions"] == 0

    def test_bfs_disclosed_semantics(self):
        ring = {(x, -1) for x in range(-1, 6)} | {(x, 5) for x in range(-1, 6)}
        ring |= {(-1, y) for y in range(-1, 6)} | {(5, y) for y in range(-1, 6)}
        assert call(M.bfs_path_length, (2, 2), (2, 2), ring) == 0
        assert call(M.bfs_path_length, (0, 0), (4, 4), ring) == 8
        sealed = ring | {(2, y) for y in range(5)}
        assert call(M.bfs_path_length, (0, 0), (4, 4), sealed) == -1

    def test_random_open_maps_always_succeed(self):
        rng = random.Random(4242)
        for _ in range(5):
            w = rng.randint(4, 8)
            h = rng.randint(4, 8)
            grid = SentryGrid(w, h, [], (w - 1, h - 1), fuel=1000)
            got = call(M.run_patrol, grid)
            assert got["success"] is True
