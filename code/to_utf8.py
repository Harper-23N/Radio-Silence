"""Convert my UTF-16 CSV downloads to plain UTF-8 and drop blank rows."""
import csv, sys

for path in sys.argv[1:]:
    with open(path, encoding="utf-16", newline="") as f:
        rows = [r for r in csv.reader(f) if any(cell.strip() for cell in r)]
    with open(path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"{path}: {len(rows) - 1} data rows, now UTF-8")