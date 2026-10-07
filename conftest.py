# -*- coding: utf-8 -*-
"""pytest 配置：让 `import main` 找到 src/main（勿改）。"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "src"))
