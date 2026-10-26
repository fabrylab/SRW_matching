# Right-whale matching: small, standalone example

Run with Python 3.10-3.13. Open a terminal in this folder and enter:

    python -m pip install -r requirements.txt
    python match.py

Choose a query from the numbered list. Both methods run by default.
To select a photograph and method directly:

    python match.py --query Query_SW0089.png --method hog
    python match.py --query Query_SW0089.png --method chamfer
    python match.py --query Query_SW0089.png --method both

On Windows, "py" can be used instead of "python" if that is your Python command.
The entire folder can be copied elsewhere. No server, database, account,
network connection, or trained model is needed after installing the packages.

## FILES

    match.py          Selects a query, calls the matching methods, prints ranks.
    HOG.py            Compares local edge-orientation descriptors.
    Chamfer.py        Compares sampled edges using capped log-chamfer distance.
    Registration.py   Prepares masks and searches for the best alignment.

There are ten Gallery_SWxxxx.png and ten Query_SWxxxx.png photographs.
Each has a separate Callosities_Gallery_SWxxxx.png or
Callosities_Query_SWxxxx.png mask. White means diagnostic callosity; black
means everything else. Matching reads these masks, not photograph intensities.
The whale codes identify the supplied examples; they are not used to calculate
similarity or choose a match.

All photographs and masks were already manually standardized to 1200 x 1000
pixels. Each gallery/query pair was photographed on different dates.
image_pairs.csv lists the dates and file correspondence. The whales were
sampled without consulting the matching results. This small set illustrates
the procedure, not population accuracy or performance against the complete
research catalogue.

## WHAT THE PROGRAM DOES

1. Extract callosity edges, crop x=225:975 and y=350:650, and reduce to 320 x 128.
2. Obtain a coarse alignment by normalized image correlation at 80 x 32.
3. Starting from that alignment and from no transformation, improve the HOG or
   chamfer distance by local changes in translation, rotation and scale.
4. Sort all ten gallery images by their final distance, separately for each
   method. Lower is better. Inspect the photographs to confirm an identity.

The alignment limits are +/-5 degrees, scale 0.80-1.20, and +/-60 ROI pixels.
Refinement steps are 1 degree, 0.01 scale, and 2 pixels. It is a local search;
it does not guarantee the best result over every possible transformation.

HOG uses 16-pixel cells, 32-pixel blocks, a 16-pixel block stride and nine bins.
Log-chamfer uses at most ten arc-length-spaced points per edge contour, a
30-pixel distance cap, log(1+distance), and both query-to-reference and
reference-to-query comparisons. The point-rotation convention is preserved
from the server and explained in Chamfer.py.

## THE GAP

The program reports g = d2 - d1, where d1 and d2 are the distances to the first
and second ranked gallery images. It also shows each distance minus d1.
A larger gap separates the best candidate more strongly from the runner-up
within this particular gallery. It is NOT a probability or a validated
accept/reject rule. Distances and gaps from HOG and chamfer use different
scales and should not be compared directly. No risk score is fitted or used.

## CHECKING THE OUTPUT

expected_rankings.csv contains all ten queries x ten references for each
method, including distances and gaps. Small floating-point differences can
occur across OpenCV versions/platforms. The example uses the server's core
preprocessing, distances and two-stage registration, with its infrastructure,
parallel workers and large caches removed for readability.

To add an image, first prepare a matching standardized photograph and binary
mask with the same dimensions and naming convention. The example does not
perform automatic segmentation or the manual standardization step.
