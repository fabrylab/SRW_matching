"""Select a query, rank ten gallery images, and report the first-to-second gap.

Run: python match.py
Or:  python match.py --query Query_SW0089.png --method hog
"""
from pathlib import Path
import argparse
from srw_matching import hog, chamfer

DATA = Path(__file__).resolve().parent / "data"
QUERY, GALLERY = DATA / "query", DATA / "gallery"


def mask_for(photo):
    """data/<set>/photos/X.png -> data/<set>/masks/Callosities_X.png"""
    return photo.parent.parent / "masks" / ("Callosities_" + photo.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", help="Query image filename; omitted = numbered menu")
    parser.add_argument("--method", choices=["hog", "chamfer", "both"], default="both")
    args = parser.parse_args()
    queries = sorted((QUERY / "photos").glob("Query_SW*.png"))
    gallery = sorted((GALLERY / "photos").glob("Gallery_SW*.png"))
    if not queries or len(gallery) < 2:
        parser.error("The example photographs must be in data/query/photos and data/gallery/photos.")
    if args.query:
        query = QUERY / "photos" / args.query
        if query not in queries:
            parser.error("Choose one of the supplied Query_SWxxxx.png files.")
    else:
        for number, path in enumerate(queries, 1):
            print(f"{number:2d}. {path.name}")
        try:
            number = int(input("Select query number: "))
            if not 1 <= number <= len(queries):
                raise ValueError
            query = queries[number - 1]
        except ValueError:
            parser.error("Please enter a number from the list.")
    print(f"\nQuery: {query.name}")
    methods = [("HOG", hog), ("Log-chamfer", chamfer)]
    if args.method != "both":
        methods = [methods[0] if args.method == "hog" else methods[1]]
    for name, method in methods:
        # Photographs are provided for inspection; matching uses their masks.
        prepared_query = method.prepare(mask_for(query))
        ranked = []
        for photo in gallery:
            reference = method.prepare(mask_for(photo))
            # Align this query-reference pair before calculating its final distance.
            distance, transform = method.match(prepared_query, reference)
            ranked.append((distance, photo.name))
        # Rank the aligned comparisons; d1 and d2 give the gap g used in the manuscript.
        ranked.sort()
        d1, d2 = ranked[0][0], ranked[1][0]
        print(f"\n{name}: smaller distance means greater similarity.")
        print("Rank  Gallery image             Distance   Difference from best")
        for rank, (distance, filename) in enumerate(ranked, 1):
            print(f"{rank:4d}  {filename:24s}  {distance:8.6f}   {distance - d1:8.6f}")
        print(f"Gap g = d2 - d1 = {d2:.6f} - {d1:.6f} = {d2 - d1:.6f}")
        print("This gap is a distance margin, not a probability of a correct match.")


if __name__ == "__main__":
    main()
