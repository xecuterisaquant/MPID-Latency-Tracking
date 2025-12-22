from pathlib import Path
from collections import Counter
import duckdb

root = Path('~/Downloads/extracted_md_zip/extracted').expanduser()
day_dirs = []
if (root / '20250310').exists():
    day_dirs.append(root / '20250310')
extra = root / 'extracted_md'
if extra.exists():
    day_dirs.extend(sorted(extra.glob('202503*')))

symbol_counter = Counter()
mpid_counter = Counter()
message_counter = Counter()
total_rows = 0
conn = duckdb.connect()

for day in day_dirs:
    day_files = [str(p) for p in day.glob('*.parquet')]
    if not day_files:
        continue
    day_rows = conn.execute("SELECT COUNT(*) FROM read_parquet($1)", [day_files]).fetchone()[0]
    total_rows += day_rows
    symbol_stats = conn.execute(
        "SELECT symbol, COUNT(*) FROM read_parquet($1) GROUP BY symbol",
        [day_files],
    ).fetchall()
    mpid_stats = conn.execute(
        "SELECT mpid, COUNT(*) FROM read_parquet($1) GROUP BY mpid",
        [day_files],
    ).fetchall()
    message_stats = conn.execute(
        "SELECT message_type, COUNT(*) FROM read_parquet($1) GROUP BY message_type",
        [day_files],
    ).fetchall()
    for symbol, count in symbol_stats:
        if symbol:
            symbol_counter[symbol] += count
    for mpid, count in mpid_stats:
        if mpid:
            mpid_counter[mpid] += count
    for msg, count in message_stats:
        if msg:
            message_counter[msg] += count

print('total_rows', total_rows)
print('unique_symbols', len(symbol_counter))
print('unique_mpids', len(mpid_counter))
print('symbol_top10', symbol_counter.most_common(10))
print('mpid_top10', mpid_counter.most_common(10))
print('message_counts', message_counter)
