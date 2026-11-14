"""
Compares every customer:{id}:categories set with PostgreSQL, size and members, and reports keys
that should not exist. Prints every difference. Exit code 1 if there is any difference, 0 otherwise.
Run: uv run --env-file .env python verify.py
"""
import sys

from rebuild import key_for, load_expected, redis_client


def main() -> int:
    r = redis_client()
    expected = load_expected()
    differences: list[str] = []

    for customer_id, categories in expected.items():
        key = key_for(customer_id)
        actual = r.smembers(key)
        if not actual:
            differences.append(f"missing key {key} (expected {len(categories)} categories)")
            continue
        if r.scard(key) != len(categories):
            differences.append(f"size of {key}: redis={r.scard(key)} postgres={len(categories)}")
        for missing in sorted(categories - actual):
            differences.append(f"{key}: missing member {missing!r}")
        for extra in sorted(actual - categories):
            differences.append(f"{key}: unexpected member {extra!r}")

    expected_keys = {key_for(c) for c in expected}
    for key in r.scan_iter(match="customer:*:categories", count=1000):   # SCAN, never KEYS
        if key not in expected_keys:
            differences.append(f"unexpected key {key} (customer has no rentals or does not exist)")

    for line in differences:
        print(line)
    print(f"{len(differences)} difference(s)")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())