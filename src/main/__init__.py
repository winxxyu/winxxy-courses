# -*- coding: utf-8 -*-
"""AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块（学生骨架）。

你的全部作业都在本文件里：按题面（题面.pdf）各题的规范补全每个标有 TODO 的函数。
- 骨架已提供：Facing / SentryState 枚举、SentryGrid 的构造与只读属性、
  渲染函数 render_frame（demo 用，不进测试）。
- 你要实现：Q1-Q6 与 Bonus 的全部 TODO，以及 SentryGrid 的
  四个方法（current_pos 的 setter、move_forward、turn_left、turn_right）。
- 未实现的函数 raise NotImplementedError：可见测试会自动 skip，
  CI 一开始就是绿的；实现一个，对应测试亮一个。
- `python main.py`（或 PYTHONPATH=src python -m main）可看 ASCII 演示。
"""
import re
import json
from enum import Enum


# ---------------------------------------------------------------------------
# 仿真世界基础（已提供，勿改）
# ---------------------------------------------------------------------------
class Facing(Enum):
    """朝向枚举。世界坐标 (x, y)：x 向右增长，y 向上增长（数学系）。"""

    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self):
        """该朝向的单位位移向量 (dx, dy)。"""
        return self.value[0], self.value[1]


# ---------------------------------------------------------------------------
# Q1 机器人自检（题面 Q1·自检状态计算与报告生成）
# ---------------------------------------------------------------------------
def hp_ratio(hp, max_hp):
    """TODO(Q1)：血量百分比，返回 0-100 的 int；计算与边界规则见题面 Q1 规范。"""
    return int(hp * 100 // max_hp)


def status_report(name, robot_type, hp, max_hp, battery):
    """TODO(Q1)：一行自检报告字符串；档位判定与逐字符格式见题面 Q1 规范。"""
    if battery >= 60:
        situation = 'OK'
    elif battery < 60 and battery >= 20:
        situation = 'WARNING'
    else:
        situation = 'LOW'
    return f"{name:<10}|{robot_type:^10}|HP {hp * 100 // max_hp:>3}%|BAT {battery:>3}%|{situation}"


# ---------------------------------------------------------------------------
# Q2 战斗日志分析（题面 Q2·多源日志解析与统计）
# ---------------------------------------------------------------------------
# Q2 行格式的字面形状（题面规范 1）

_SENSOR_SEG_RE = re.compile(r"^([FLR]):([0-9]+)$")
_ARMOR_OF_LETTER = {"F": "front", "L": "left", "R": "right"}
_ARMOR_KEYS = ("front", "left", "right")
_MISSING = object()          # 标记 JSON 行没有 id 字段


def _parse_sensor_line(line):
    """传感器行 → [(armor, damage), ...]；任一段不合格式整行作废，返回 None。"""
    events = []
    for segment in line.split(","):
        matched = _SENSOR_SEG_RE.match(segment.strip())
        if matched is None:                      # 规范 2/5：字段非法
            return None
        damage = int(matched.group(2))
        if damage <= 0:                          # 规范 5：必须是正整数
            return None
        events.append((_ARMOR_OF_LETTER[matched.group(1)], damage))
    return events or None


def _parse_json_line(line):
    """JSON 行 → (armor, damage, id)；id 缺失时为 _MISSING，脏行返回 None。"""
    if not line.startswith("{"):
        return None
    try:
        record = json.loads(line)
    except (ValueError, TypeError):              # 规范 3：解析不得抛异常
        return None
    if not isinstance(record, dict):
        return None
    armor, damage = record.get("armor"), record.get("damage")
    if armor not in _ARMOR_KEYS:                 # 规范 4：部位必须是三者之一
        return None
    if isinstance(damage, bool) or not isinstance(damage, int):
        return None                              # 规范 4：严格正整数
    if damage <= 0:
        return None
    return armor, damage, record.get("id", _MISSING)


def analyze_damage_log(lines):
    """TODO(Q2)：解析混合格式伤害日志，返回固定契约的统计 dict。"""
    by_armor = {key: 0 for key in _ARMOR_KEYS}   # 规范 7：三键恒存在
    total = 0
    event_count = 0
    counted_ids = set()
    try:
        rows = iter(lines)
    except TypeError:
        rows = ()
    for line in rows:
        if not isinstance(line, str):
            continue
        line = line.strip()
        if not line or line.startswith("#"):     # 规范 2：空行 / 注释
            continue
        if line.startswith("{"):                 # —— 分流开关
            parsed = _parse_json_line(line)
            if parsed is None:
                continue
            armor, damage, event_id = parsed
            if event_id is not _MISSING:         # 规范 6：带 id 去重
                try:
                    if event_id in counted_ids:
                        continue
                    counted_ids.add(event_id)
                except TypeError:                # id 不可哈希：退化为独立计数
                    pass
            pairs = [(armor, damage)]
        else:
            pairs = _parse_sensor_line(line)
            if pairs is None:
                continue
        for armor, damage in pairs:              # 传感器行无 id，逐段各算一次事件
            by_armor[armor] += damage
            total += damage
            event_count += 1
    most_hit = None                              # 规范 7：受击伤害最大的部位
    for key in _ARMOR_KEYS:                      # 并列时按 front/left/right 取先者
        if by_armor[key] and (most_hit is None
                              or by_armor[key] > by_armor[most_hit]):
            most_hit = key
    return {"total": total,
            "by_armor": by_armor,
            "most_hit": most_hit,
            "avg": round(total / event_count, 2) if event_count else 0.0}

# ---------------------------------------------------------------------------
# Q3 SentryGrid（题面 Q3·载体物理规则）
# ---------------------------------------------------------------------------


class SentryGrid:
    """哨兵仿真载体（构造与只读属性已提供；四个 TODO 方法由你实现）。"""

    def __init__(self, width, height, obstacles, enemy_pos,
                 start_pos=(0, 0), facing=Facing.UP, fuel=100):
        self._width = int(width)
        self._height = int(height)
        if self._width <= 0 or self._height <= 0:
            raise ValueError("地图尺寸必须为正")
        # 障碍坐标存入 set，查询 O(1)——已有实现，勿改。
        self._obstacles = set()
        for ob in obstacles:
            x, y = ob
            self._obstacles.add((int(x), int(y)))
        if not isinstance(enemy_pos, (tuple, list)) or len(enemy_pos) != 2:
            raise TypeError("enemy_pos 需要长度为 2 的 tuple/list")
        self._enemy_pos = self._clamp_cell(enemy_pos)
        if self._enemy_pos in self._obstacles:
            raise ValueError("enemy_pos 不能位于障碍物上")
        if not isinstance(facing, Facing):
            facing = Facing.UP
        self._facing = facing
        self._fuel = int(fuel)
        self._collision_count = 0
        self.current_pos = start_pos

    def _clamp_cell(self, cell):
        """已提供：元素转 int 并夹回地图范围（供 __init__ 使用）。"""
        x = int(cell[0])
        y = int(cell[1])
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    # -- 只读属性（已提供，勿改） ------------------------------------------
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def enemy_pos(self):
        return self._enemy_pos

    @property
    def facing(self):
        return self._facing

    @property
    def fuel(self):
        return self._fuel

    @property
    def collision_count(self):
        return self._collision_count

    @property
    def obstacles(self):
        """障碍集合的只读视图（内部 set 引用，不要修改它）。"""
        return self._obstacles

    @property
    def found_enemy(self):
        return self._pos == self._enemy_pos

    def is_blocked(self, x, y):
        """已提供：坐标是否为障碍或越界（O(1)）。"""
        return ((x, y) in self._obstacles
                or not (0 <= x < self._width and 0 <= y < self._height))

    # -- 你要实现的部分 ------------------------------------------------------
    @property
    def current_pos(self):
        """当前位置 (x, y) 的 tuple。"""
        return self._pos

    @current_pos.setter
    def current_pos(self, value):
        """TODO(Q3)：位置 setter；三重输入校验见题面 Q3 规范第 1 条。"""
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise TypeError
        else:
            setter = (int(value[0]), int(value[1]))
            self._pos = setter

    def move_forward(self):
        """TODO(Q3)：朝当前 facing 前进一格，返回执行后的位置；
        碰撞、耗电与断电语义见题面 Q3 规范。"""
        if self._fuel <= 0:
            return self._pos
        else:
            x, y = self._pos
            dx, dy = self._facing.delta
            new_x, new_y = x + dx, y + dy
            if self.is_blocked(new_x, new_y):
                self._collision_count += 1
                self._fuel -= 1
                return self._pos
            else:
                self._pos = (new_x, new_y)
                self._fuel -= 1
                return self._pos

    def turn_left(self):
        """TODO(Q3)：原地左转 90°，返回新的 Facing（不耗电）。"""
        if self._facing == Facing.UP:
            self._facing = Facing.LEFT
        elif self._facing == Facing.LEFT:
            self._facing = Facing.DOWN
        elif self._facing == Facing.DOWN:
            self._facing = Facing.RIGHT
        else:
            self._facing = Facing.UP
        return self.facing

    def turn_right(self):
        """TODO(Q3)：原地右转 90°，返回新的 Facing（不耗电）。"""
        if self._facing == Facing.UP:
            self._facing = Facing.RIGHT
        elif self._facing == Facing.RIGHT:
            self._facing = Facing.DOWN
        elif self._facing == Facing.DOWN:
            self._facing = Facing.LEFT
        else:
            self._facing = Facing.UP
        return self.facing

# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------


def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """TODO(Q4)：返回下一步应朝向的 Facing；
    候选判定、优先级与回退规则见题面 Q4 规范。"""
    x, y = pos
    tx, ty = target
    dx = tx - x
    dy = ty - y
    if dx > dy:
        if dx > 0 and (x + 1, y) not in obstacles:
            current_facing = Facing.RIGHT
        elif dx < 0 and (x - 1, y) not in obstacles:
            current_facing = Facing.LEFT
        else:
            if dy > 0 and (x, y + 1) not in obstacles:
                current_facing = Facing.UP
            elif dy < 0 and (x, y - 1) not in obstacles:
                current_facing = Facing.DOWN
            else:
                pass
    elif dy > dx:
        if dy > 0 and (x, y+1) not in obstacles:
            current_facing = Facing.UP
        elif dy < 0 and (x, y-1) not in obstacles:
            current_facing = Facing.DOWN
        else:
            if dx > 0 and (x + 1, y) not in obstacles:
                current_facing = Facing.RIGHT
            elif dx < 0 and (x - 1, y) not in obstacles:
                current_facing = Facing.LEFT
            else:
                pass
    else:                                        # dx == dy：两轴距离相等
        if dy >= 0 and (x, y + 1) not in obstacles:
            current_facing = Facing.UP
        elif dy < 0 and (x, y - 1) not in obstacles:
            current_facing = Facing.DOWN
        elif dx < 0 and (x - 1, y) not in obstacles:
            current_facing = Facing.LEFT
        elif dx > 0 and (x + 1, y) not in obstacles:
            current_facing = Facing.RIGHT

    return current_facing

# Q5 哨兵决策机（题面 Q5·裁判系统决策规则表）
# ---------------------------------------------------------------------------


class SentryState(Enum):
    """哨兵状态机（已提供，勿改）。"""

    PATROL = "PATROL"
    SUSPECT = "SUSPECT"
    ENGAGE = "ENGAGE"
    RETREAT = "RETREAT"
    RETURN = "RETURN"


def decide(sensor, state, hp, heat):
    """TODO(Q5)：纯函数决策，返回 (action: str, new_state: SentryState)；
    sensor 字段契约、R1-R7 规则表与非法输入处理见题面 Q5 规范。"""

    for key in ("enemy_frames", "enemy_dist", "robot_type", "max_hp"):
        if key not in sensor:
            raise ValueError("sensor 缺少字段: %s" % key)
    if len(sensor["enemy_frames"]) > 6 or len(sensor["enemy_frames"]) == 0:
        raise ValueError("sensor['enemy_frames'] 长度超过 6")
    if not isinstance(state, SentryState):
        raise ValueError("state 非法")

    def isVisiable(sensor):
        if len(sensor["enemy_frames"]) >= 2 and sensor["enemy_frames"][-1] and sensor["enemy_frames"][-2]:
            return True
        else:
            return False

    def howFire(sensor):
        if sensor["enemy_dist"] <= 3 and sensor["enemy_dist"] is not None:
            state = SentryState.ENGAGE
            return "SHOOT", SentryState.ENGAGE
        else:
            if sensor["robot_type"] == "HERO":
                state = SentryState.ENGAGE
                return "MOVE_RIGHT", SentryState.ENGAGE
            else:
                state = SentryState.ENGAGE
                return "MOVE_LEFT", SentryState.ENGAGE

    max_hp = sensor["max_hp"] if sensor["max_hp"] else 1
    hp_pct = hp * 100 // max_hp
    if hp_pct <= 30:
        state = SentryState.RETREAT
        return "RETREAT", SentryState.RETREAT
    else:
        if state == SentryState.RETREAT:
            if hp_pct > 30:
                state = SentryState.RETURN
                return "RETURN", SentryState.RETURN
            else:
                return "RETREAT", SentryState.RETREAT
        elif state == SentryState.RETURN:
            state = SentryState.PATROL
            return "MOVE_BASE", SentryState.PATROL
        elif state == SentryState.ENGAGE:
            if sensor["enemy_frames"][-1]:
                return howFire(sensor)
            else:
                if sensor["enemy_frames"][-2]:
                    return "HOLD_FIRE", SentryState.ENGAGE
                else:
                    state = SentryState.SUSPECT
                    return "SCAN", SentryState.SUSPECT
        elif state == SentryState.PATROL or state == SentryState.SUSPECT:
            if sensor["enemy_frames"][-1]:
                if isVisiable(sensor):
                    return howFire(sensor)
                else:
                    state = SentryState.SUSPECT
                    return "SCAN", SentryState.SUSPECT
            else:
                if state == SentryState.SUSPECT:
                    return "SCAN", SentryState.SUSPECT
                else:
                    return "PATROL_MOVE", SentryState.PATROL

# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------


def run_patrol(grid, max_steps=500):
    """TODO(Q6)：sense → decide → act 主循环；
    循环结构、终止条件、脱困自由度与统计返回契约见题面 Q6 规范。"""
    step = 0
    visited = {grid.current_pos}

    def Move(grid, target_facing):
        nonlocal step
        while grid.facing != target_facing:
            if (grid.facing == Facing.UP and target_facing == Facing.LEFT) or (
                    grid.facing == Facing.LEFT and target_facing == Facing.DOWN) or (
                    grid.facing == Facing.DOWN and target_facing == Facing.RIGHT) or (
                    grid.facing == Facing.RIGHT and target_facing == Facing.UP):
                grid.turn_left()
            else:
                grid.turn_right()
        x, y = grid.current_pos
        dx, dy = grid.facing.delta
        if grid.is_blocked(x + dx, y + dy):      # 新增：前方是墙就不迈腿
            return False
        grid.move_forward()
        visited.add(grid.current_pos)
        step += 1
        return True

    def wall_follow(grid):
        while grid.fuel > 0 and not grid.found_enemy and step < max_steps:
            x, y = grid.current_pos
            if grid.facing == Facing.UP:
                if not grid.is_blocked(x - 1, y):
                    Move(grid, Facing.LEFT)
                    break
                elif not grid.is_blocked(x, y + 1):
                    Move(grid, Facing.UP)
                else:
                    Move(grid, Facing.RIGHT)
            elif grid.facing == Facing.DOWN:
                if not grid.is_blocked(x + 1, y):
                    Move(grid, Facing.RIGHT)
                elif not grid.is_blocked(x, y - 1):
                    Move(grid, Facing.DOWN)
                else:
                    Move(grid, Facing.LEFT)
                    break
            elif grid.facing == Facing.LEFT:
                if not grid.is_blocked(x, y - 1):
                    Move(grid, Facing.DOWN)
                elif not grid.is_blocked(x - 1, y):
                    Move(grid, Facing.LEFT)
                    break
                else:
                    Move(grid, Facing.UP)
            elif grid.facing == Facing.RIGHT:
                if not grid.is_blocked(x, y + 1):
                    Move(grid, Facing.UP)
                elif not grid.is_blocked(x + 1, y):
                    Move(grid, Facing.RIGHT)
                else:
                    Move(grid, Facing.DOWN)

    x, y = grid.current_pos
    while step < max_steps and not grid.found_enemy and grid.fuel > 0:
        next_facing = next_step_toward(
            grid.current_pos, grid.enemy_pos, grid.obstacles, grid.facing)
        if Move(grid, next_facing):
            continue
        before = step
        wall_follow(grid)
        if step == before:
            break

    return {"steps": step,
            "collisions": grid.collision_count,
            "visited_count": len(visited),
            "found_enemy": grid.found_enemy,
            "success": grid.found_enemy}


def report_to_json(stats):
    """TODO(Q6)：把 stats 序列化为确定性的 JSON 字符串，见题面 Q6 规范。"""
    return json.dumps(stats, sort_keys=True)

# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路（题面 Bonus·BFS 语义与排行榜）
# ---------------------------------------------------------------------------


def bfs_path_length(start, target, obstacles):
    """TODO(Bonus)：BFS 全局最短路步数；返回语义与边界职责见题面 Bonus 规范。"""
    raise NotImplementedError("Bonus bfs_path_length")


# ---------------------------------------------------------------------------
# 渲染（已提供，demo 专用，不进测试）
# ---------------------------------------------------------------------------
def render_frame(grid, trail=()):
    """ASCII 渲染一帧战场；trail 为走过的格子集合。返回 list[str]。"""
    trail = set(trail)
    rows = []
    for y in range(grid.height - 1, -1, -1):
        row = []
        for x in range(grid.width):
            if (x, y) == grid.current_pos:
                row.append("◉")
            elif (x, y) == grid.enemy_pos:
                row.append("▲")
            elif (x, y) in grid.obstacles:
                row.append("█")
            elif (x, y) in trail:
                row.append("·")
            else:
                row.append(".")
        rows.append("".join(row))
    return rows
