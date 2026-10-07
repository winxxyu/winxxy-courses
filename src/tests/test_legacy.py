# -*- coding: utf-8 -*-
"""Q7 可见测试。"""
import main.legacy_patrol as L


class TestQ7:
    def test_route_meters(self):
        assert L.total_route_meters([(0, 0), (3, 0), (3, 4)]) == 7

    def test_calibrate_no_positive(self):
        assert L.calibrate([]) == 0
        assert L.calibrate([-1, -2]) == 0
        assert L.calibrate([2, 3, 5]) == 4

    def test_log_default_history_independent(self):
        assert L.log("a") == ["a"]
        assert L.log("b") == ["b"]
        assert L.log("c", ["x"]) == ["x", "c"]

    def test_summarize_includes_max_id(self):
        events = [{"id": 1, "move": 10, "samples": [1, 2]},
                  {"id": 2, "move": 4, "samples": [-5]}]
        assert L.summarize_events(events, 2) == {"events": 2, "steps": 15}

    def test_sim_basic_run(self):
        got = L.run_legacy_sim(10, 100)
        assert got["rounds"] == 8
        assert got["stamina"] == 11
        assert got["trace"][0] == (0, 92)
        assert got["trace"][3] == (3, 63)      # 第 4 轮起额外 -5

    def test_sim_stops_at_threshold(self):
        got = L.run_legacy_sim(2, 28)
        assert got == {"rounds": 1, "stamina": 20, "trace": [(0, 20)]}
        got = L.run_legacy_sim(3, 100)
        assert got["rounds"] == 3              # 体力充足则跑满轮数

    def test_parse_event(self):
        assert L.parse_event("MOVE,3") == {"type": "MOVE", "count": 3}
        assert L.parse_event("FLY,3") is None
        assert L.parse_event("MOVE,x") is None
