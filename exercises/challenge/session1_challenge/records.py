import json
import multiprocessing as mp
import os
import time
from pathlib import Path

import psycopg

N_PROCS = 10
N_RECORDS = 1000
JSON_PATH = Path("records.json")

DSN = (
    f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
    f"port={os.getenv('POSTGRES_PORT', '5432')} "
    f"dbname={os.getenv('POSTGRES_DB', 'postgres')} "
    f"user={os.getenv('POSTGRES_USER', 'postgres')} "
    f"password={os.getenv('POSTGRES_PASSWORD', '')}"
)


# ---------- JSON: ler, acrescentar, escrever (sem proteção) ----------

def json_worker(worker_id: int) -> None:
    read_errors = 0
    for i in range(N_RECORDS):
        try:
            data = json.loads(JSON_PATH.read_text())     # ler
            data.append({"worker": worker_id, "i": i})   # acrescentar
            JSON_PATH.write_text(json.dumps(data))       # escrever
        except json.JSONDecodeError:
            # outro processo estava a meio de escrever o ficheiro
            read_errors += 1
    if read_errors:
        print(f"worker {worker_id}: {read_errors} leituras inválidas")


def run_json() -> int:
    JSON_PATH.write_text("[]")
    procs = [mp.Process(target=json_worker, args=(w,)) for w in range(N_PROCS)]
    start = time.perf_counter()
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    elapsed = time.perf_counter() - start

    try:
        count = len(json.loads(JSON_PATH.read_text()))
    except json.JSONDecodeError:
        count = -1  # ficheiro corrompido

    print(f"JSON: {count} registos em {elapsed:.2f}s (esperado: {N_PROCS * N_RECORDS})")
    return count


# ---------- PostgreSQL: 10 ligações concorrentes ----------

def pg_worker(worker_id: int) -> None:
    with psycopg.connect(DSN, autocommit=True) as conn:
        with conn.cursor() as cur:
            for i in range(N_RECORDS):
                cur.execute(
                    "INSERT INTO challenge_records (worker, i) VALUES (%s, %s)",
                    (worker_id, i),
                )


def run_postgres() -> int:
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS challenge_records")
        conn.execute(
            """
            CREATE TABLE challenge_records (
                id      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                worker  INT NOT NULL,
                i       INT NOT NULL
            )
            """
        )

    procs = [mp.Process(target=pg_worker, args=(w,)) for w in range(N_PROCS)]
    start = time.perf_counter()
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    elapsed = time.perf_counter() - start

    with psycopg.connect(DSN) as conn:
        count = conn.execute("SELECT COUNT(*) FROM challenge_records").fetchone()[0]

    print(f"PostgreSQL: {count} registos em {elapsed:.2f}s (esperado: {N_PROCS * N_RECORDS})")
    return count


if __name__ == "__main__":
    run_json()
    run_postgres()