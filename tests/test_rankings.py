"""Check every query and method against tests/expected_rankings.csv.

Run from the repository folder:  python tests/test_rankings.py
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from match import QUERY, GALLERY, mask_for  # noqa: E402
from srw_matching import hog, chamfer  # noqa: E402

TOLERANCE = 1e-4  # Small floating-point differences across OpenCV versions are fine.


def main():
    expected = {}
    with open(Path(__file__).with_name("expected_rankings.csv"), newline="") as f:
        for row in csv.DictReader(f):
            expected[(row["method"], row["query"], int(row["rank"]))] = row
    gallery = sorted((GALLERY / "photos").glob("Gallery_SW*.png"))
    failures = 0
    for name, method in [("hog", hog), ("chamfer", chamfer)]:
        references = [(photo.name, method.prepare(mask_for(photo))) for photo in gallery]
        for query in sorted((QUERY / "photos").glob("Query_SW*.png")):
            prepared = method.prepare(mask_for(query))
            ranked = sorted((method.match(prepared, ref)[0], filename)
                            for filename, ref in references)
            for rank, (distance, filename) in enumerate(ranked, 1):
                row = expected[(name, query.name, rank)]
                if filename != row["gallery"] or abs(distance - float(row["distance"])) > TOLERANCE:
                    failures += 1
                    print(f"MISMATCH {name} {query.name} rank {rank}: "
                          f"{filename} {distance:.6f} vs {row['gallery']} {float(row['distance']):.6f}")
            print(f"checked {name:8s} {query.name}")
    print("All rankings match." if not failures else f"{failures} mismatches.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
