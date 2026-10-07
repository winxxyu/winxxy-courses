# -*- coding: utf-8 -*-
"""演示入口：`python main.py`（维护者文件，勿改）。
等价于 PYTHONPATH=src python -m main。"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "src"))

from main.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
