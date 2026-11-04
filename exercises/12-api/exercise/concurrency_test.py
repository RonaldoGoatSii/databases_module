"""
Sends 5 simultaneous POST /rentals for film 7 in store 1 (customers 1 to 5, staff 6).
Film 7 has exactly 2 copies in store 1 on a fresh copy, so the expected result is two 201 and three 409.
Run the API first (see README), then:
    uv run python concurrency_test.py
"""
import os
import sys
import threading
from collections import Counter

import httpx

API = os.environ.get("API_URL", "http://127.0.0.1:8000")
N = 5
barrier = threading.Barrier(N)
results: list[tuple[int, dict]] = [None] * N  # type: ignore[list-item]


def send(i: int) -> None:
    body = {"customer_id": i + 1, "film_id": 7, "store_id": 1, "staff_id": 6}
    barrier.wait()  # all threads start at the same moment
    response = httpx.post(f"{API}/rentals", json=body, timeout=30)
    results[i] = (response.status_code, response.json())


def main() -> int:
    threads = [threading.Thread(target=send, args=(i,)) for i in range(N)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for i, (status, payload) in enumerate(results):
        print(f"customer {i + 1}: {status} {payload}")
    counts = Counter(status for status, _ in results)
    inventories = {p["inventory_id"] for status, p in results if status == 201}
    print(f"\n201: {counts[201]}  409: {counts[409]}  distinct inventory_id: {sorted(inventories)}")

    ok = counts[201] == 2 and counts[409] == 3 and len(inventories) == 2
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())