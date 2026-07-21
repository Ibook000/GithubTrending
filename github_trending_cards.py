#!/usr/bin/env python3
"""向后兼容入口：运行 GitHub 趋势雷达生成器。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from github_trending.app import *  # noqa: F403,E402
from github_trending.app import main

if __name__ == "__main__":
    main()
