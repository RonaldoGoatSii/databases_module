"""
Measures each query of queries.sql with EXPLAIN (ANALYZE, BUFFERS), 3 times, and prints the median.
Usage (from the repository root):
    python3 exercises/07-indexes/exercise/measure.py ex07 before
    python3 exercises/07-indexes/exercise/measure.py ex07 after
Writes the plans to exercises/07-indexes/exercise/plans_<label>.txt
"""
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB, LABEL = sys.argv[1], sys.argv[2]


def load_queries():
    queries, label, lines = {}, None, []
    for line in (HERE / "queries.sql").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^-- (Q\w+)", line)
        if m:
            if label:
                queries[label] = "\n".join(lines).strip()
            label, lines = m.group(1), []
        elif label and line.strip() and not line.startswith("--"):
            lines.append(line)
    if label:
        queries[label] = "\n".join(lines).strip()
    return queries


def explain(sql):
    cmd = ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "postgres",
           "-d", DB, "-At", "-c", f"EXPLAIN (ANALYZE, BUFFERS) {sql}"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    ms = float(re.search(r"Execution Time: ([\d.]+) ms", out).group(1))
    return out, ms


def main():
    queries = load_queries()
    report = []
    for name, sql in queries.items():
        runs = [explain(sql) for _ in range(3)]
        median = statistics.median(ms for _, ms in runs)
        plan = runs[1][0]
        report.append(f"=== {name}: median {median:.1f} ms (runs: {', '.join(f'{ms:.1f}' for _, ms in runs)})")
        report.append(sql)
        report.append(plan)
        report.append("")
        print(f"{name}: median {median:.1f} ms")
    (HERE / f"plans_{LABEL}.txt").write_text("\n".join(report), encoding="utf-8")
    print(f"Plans written to plans_{LABEL}.txt")


if __name__ == "__main__":
    main()