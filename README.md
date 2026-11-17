# The complexity of counting relevant cuts in graphs

Marek Gałązka and Hanna Wdowicka

The program [verify.py](verify.py) reproduces the finite checks in the paper,
including the counts reported in Table 1. It requires
Python 3.10 or later and uses only its standard library. All graphs are
generated locally.

## Reproduce Table 1

Run the following in the directory containing this file.

    python3 verify.py > reproduced.csv

The expected output is [results.csv](results.csv). On Windows, `py -3 verify.py` runs the
same program. To compare the results on any platform, use the command below.

    python3 -c "from pathlib import Path as P; assert P('results.csv').read_text().splitlines() == P('reproduced.csv').read_text().splitlines()"

A shorter run through order four is available with `python3 verify.py --max-order 4`.
The program raises an exception at the first failed check.

## Counts recorded in the CSV

| Column | Meaning |
| --- | --- |
| `order` | Number of vertices in the initial graph |
| `graphs` | Connected simple graphs of this order up to isomorphism |
| `terminal_pairs` | Unordered vertex pairs, summed over the chosen graph representatives |
| `tree_orders` | Two runs for each graph, using an order of one certified cut tree and its reverse. The runs coincide for a one-edge tree. |
| `long_path_pairs` | Pairs checked separately for path addition and uniform subdivision at lengths three and four |
| `composed_pairs` | Pairs tested on the subdivided bipartite graph of Theorem 1.1 with path length two |

The default run covers 142 graphs and 1,933 graph/terminal-pair instances.
All 43 pairs through order four also undergo the longer-path tests and the
full construction of Theorem 1.1 at length two. Length three tests the path
identity and the subdivision lemma, which require no bipartiteness. Extra
checks cover the four-cycle, the example one below the degree threshold,
the planar graphs K_{2,h} for h from 1 through 6, a parallel-edge input and
one full length-four construction of girth eight. These extra examples are
outside the table totals.

## Independent checks

The program enumerates labelled edge masks and removes duplicates by taking
permutation orbits. A nontrivial shore of weight zero detects disconnected
graphs. The last vertex is fixed outside the shore so every cut appears once.
Binary elimination on the shore vectors computes the relevant-cut histogram
from independence modulo strictly cheaper cuts. On a connected graph this
representation is linearly isomorphic to the edge-cut space.

For each of the 142 base graphs, a second enumeration constructs the actual
boundary edge sets for every shore. It collects all minimum edge sets for
each terminal pair, takes their set union, and groups the union by size.
The program compares this direct count to the binary-elimination profile.

For the path formula, fixed-terminal counts come from direct minimization
over separating shores. Both the augmented graph and the terminal quotient
are independently counted by binary elimination. The two choices of the
number of added paths are the least positive value meeting the degree threshold
and the original order. They are tested once when they coincide.

For the cut-tree formula the program examines labelled trees via Prüfer
sequences until every fundamental cut attains the independently computed
minimum between the endpoints of its tree edge. These conditions certify a
Gomory–Hu tree. For a given pair, every separating cut crosses a path edge,
and the fundamental cut of a lightest path edge attains the path minimum.
The counts in the contracted graphs are obtained by exhaustive fixed-pair
minimization and compared with the whole binary-elimination histogram.

The exhaustive algorithms make the experiments transparent at these small
orders. The running-time theorems in the paper use the cited polynomial-time
cut-tree construction and the parameterized fixed-pair counting algorithm.
