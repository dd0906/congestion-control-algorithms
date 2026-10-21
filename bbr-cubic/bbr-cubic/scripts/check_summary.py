#!/usr/bin/env python3
import json
import sys

for path in sys.argv[1:]:
    with open(path) as f:
        d = json.load(f)
    print(f"=== {path} ===")
    print("avg mbps:", d["end"]["sum_received"]["bits_per_second"] / 1e6)
    for i in d["intervals"]:
        print(round(i["sum"]["end"]), round(i["sum"]["bits_per_second"] / 1e6, 2))
