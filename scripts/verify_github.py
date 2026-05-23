#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 GitHub 仓库内容。"""

import urllib.request
import json

url = "https://api.github.com/repos/kercome/ROCO-KINGDOM/contents/"
req = urllib.request.Request(url, headers={"User-Agent": "Python"})

try:
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
        print(f"GitHub 仓库根目录（共 {len(data)} 项）：")
        for f in data:
            t = f["type"]
            n = f["name"]
            print(f"  {t:6s}  {n}")
except Exception as e:
    print(f"API 请求失败：{e}")
