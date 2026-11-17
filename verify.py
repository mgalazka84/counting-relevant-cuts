"""Finite checks for The complexity of counting relevant cuts in graphs.

Run with Python 3.10 or later. Output is deterministic CSV on standard output.
Parallel edges are separate entries. Graphs have vertices 0,...,n-1.
"""

import argparse
import csv
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations, permutations, product


@dataclass(frozen=True)
class Graph:
    n: int
    edges: tuple


def edge_weights_by_shore(graph):
    """Index a cut by its unique shore omitting the last vertex."""
    incident = [0] * graph.n
    for index, (u, v) in enumerate(graph.edges):
        incident[u] |= 1 << index
        incident[v] |= 1 << index
    weights = [0] * (1 << (graph.n - 1))
    previous = edge_mask = 0
    for i in range(1, len(weights)):
        shore = i ^ (i >> 1)
        changed = (shore ^ previous).bit_length() - 1
        edge_mask ^= incident[changed]
        weights[shore] = edge_mask.bit_count()
        previous = shore
    return weights


def reduce_vector(vector, rows):
    while vector and vector.bit_length() in rows:
        vector ^= rows[vector.bit_length()]
    return vector


def relevant_histogram(weights):
    """Test independence from *strictly* cheaper cuts before extending a layer."""
    layers = defaultdict(list)
    for shore in range(1, len(weights)):
        layers[weights[shore]].append(shore)
    rows = {}
    histogram = Counter()
    for weight, shores in sorted(layers.items()):
        count = sum(bool(reduce_vector(shore, rows)) for shore in shores)
        if count:
            histogram[weight] = count
        for shore in shores:
            vector = reduce_vector(shore, rows)
            if vector:
                rows[vector.bit_length()] = vector
    return histogram


def fixed_pair(weights, u, v):
    minimum = None
    count = 0
    for shore, weight in enumerate(weights):
        if ((shore >> u) ^ (shore >> v)) & 1:
            if minimum is None or weight < minimum:
                minimum, count = weight, 1
            elif weight == minimum:
                count += 1
    return minimum, count


def quotient(graph, pairs):
    parent = list(range(graph.n))

    def root(v):
        while parent[v] != v:
            v = parent[v]
        return v

    for u, v in pairs:
        parent[root(v)] = root(u)
    roots = [root(v) for v in range(graph.n)]
    labels = {r: i for i, r in enumerate(sorted(set(roots)))}
    images = [labels[r] for r in roots]
    edges = tuple((images[u], images[v]) for u, v in graph.edges
                  if images[u] != images[v])
    return Graph(len(labels), edges), images


def add_paths(graph, s, t, k, length=2):
    edges = list(graph.edges)
    next_vertex = graph.n
    for _ in range(k):
        interior = list(range(next_vertex, next_vertex + length - 1))
        path = [s, *interior, t]
        edges.extend(zip(path, path[1:]))
        next_vertex += length - 1
    return Graph(next_vertex, tuple(edges))


def subdivision(graph, length=2):
    edges = []
    next_vertex = graph.n
    for u, v in graph.edges:
        interior = list(range(next_vertex, next_vertex + length - 1))
        path = [u, *interior, v]
        edges.extend(zip(path, path[1:]))
        next_vertex += length - 1
    return Graph(next_vertex, tuple(edges))


def connected_representatives(n):
    all_edges = list(combinations(range(n), 2))
    index = {edge: i for i, edge in enumerate(all_edges)}
    permutations_of_edges = [
        [1 << index[tuple(sorted((p[u], p[v])))] for u, v in all_edges]
        for p in permutations(range(n))
    ]
    seen = set()
    for mask in range(1, 1 << len(all_edges)):
        if mask in seen:
            continue
        indices = [j for j in range(len(all_edges)) if (mask >> j) & 1]
        for perm in permutations_of_edges:
            seen.add(sum(perm[j] for j in indices))
        graph = Graph(n, tuple(all_edges[j] for j in indices))
        if 0 not in edge_weights_by_shore(graph)[1:]:
            yield graph


@lru_cache(maxsize=None)
def labelled_trees(n):
    """Precompute the fundamental shores for all Pruefer trees of order n."""
    trees = []
    for sequence in product(range(n), repeat=n - 2):
        degree = [1] * n
        for vertex in sequence:
            degree[vertex] += 1
        edges = []
        for vertex in sequence:
            leaf = next(i for i, d in enumerate(degree) if d == 1)
            edges.append(tuple(sorted((leaf, vertex))))
            degree[leaf] -= 1
            degree[vertex] -= 1
        edges.append(tuple(i for i, d in enumerate(degree) if d == 1))
        neighbours = [[] for _ in range(n)]
        for u, v in edges:
            neighbours[u].append(v)
            neighbours[v].append(u)
        fundamental = []
        for u, v in sorted(edges):
            stack, visited = [u], {u, v}
            shore = 0
            while stack:
                a = stack.pop()
                shore |= 1 << a
                for b in neighbours[a]:
                    if b not in visited:
                        visited.add(b)
                        stack.append(b)
            if shore >> (n - 1):
                shore ^= (1 << n) - 1
            fundamental.append((u, v, shore))
        trees.append(fundamental)
    return trees


def verified_cut_tree(graph, weights, pair_data):
    for tree in labelled_trees(graph.n):
        if all(weights[a] == pair_data[u, v][0] for u, v, a in tree):
            return [(u, v, weights[a]) for u, v, a in tree]
    raise RuntimeError("no cut tree found")


def tree_histogram(graph, tree):
    histogram = Counter()
    earlier = defaultdict(list)
    for u, v, weight in tree:
        small, images = quotient(graph, earlier[weight])
        value, count = fixed_pair(edge_weights_by_shore(small), images[u], images[v])
        if value != weight:
            raise AssertionError(("quotient minimum", graph, tree, u, v, value))
        histogram[weight] += count
        earlier[weight].append((u, v))
    return histogram


def check_order(n):
    graphs = pairs = longer = composed = 0
    for graph in connected_representatives(n):
        graphs += 1
        weights = edge_weights_by_shore(graph)
        expected = relevant_histogram(weights)
        pair_data = {p: fixed_pair(weights, *p) for p in combinations(range(n), 2)}
        tree = verified_cut_tree(graph, weights, pair_data)
        for ordering in (tree, list(reversed(tree))):
            if tree_histogram(graph, ordering) != expected:
                raise AssertionError(("tree histogram", graph, ordering))
        degrees = Counter(v for edge in graph.edges for v in edge)
        for (s, t), (lam, count) in pair_data.items():
            pairs += 1
            small, _ = quotient(graph, [(s, t)])
            remainder = sum(relevant_histogram(edge_weights_by_shore(small)).values())
            d = max([2] + [degrees[v] for v in range(n) if v not in (s, t)])
            for k in sorted({max(1, d - lam), n}):
                augmented = add_paths(graph, s, t, k)
                actual = sum(relevant_histogram(edge_weights_by_shore(augmented)).values())
                if actual != (count << k) + remainder + k:
                    raise AssertionError(("path identity", graph, s, t, k, actual))
                if k == n and actual >> n != count:
                    raise AssertionError(("binary extraction", graph, s, t))
            if n <= 4:
                for length in (3, 4):
                    for k in sorted({max(1, d - lam), n}):
                        augmented = add_paths(graph, s, t, k, length)
                        actual = sum(relevant_histogram(edge_weights_by_shore(augmented)).values())
                        intervals = k * length * (length - 1) // 2
                        if actual != length ** k * count + remainder + intervals:
                            raise AssertionError(("longer paths", graph, s, t, k, length))
                    divided = subdivision(graph, length)
                    if fixed_pair(edge_weights_by_shore(divided), s, t) != (lam, count * length ** lam):
                        raise AssertionError(("longer subdivision", graph, s, t, length))
                longer += 1
                divided = subdivision(graph)
                if fixed_pair(edge_weights_by_shore(divided), s, t) != (lam, count << lam):
                    raise AssertionError(("subdivision", graph, s, t))
                restricted = add_paths(divided, s, t, divided.n)
                total = sum(relevant_histogram(edge_weights_by_shore(restricted)).values())
                if total >> (divided.n + lam) != count:
                    raise AssertionError(("bipartite reduction", graph, s, t))
                composed += 1
    return n, graphs, pairs, 2 * graphs, longer, composed


def check_worked_examples():
    cycle = Graph(4, ((0, 1), (1, 2), (2, 3), (3, 0)))
    weights = edge_weights_by_shore(cycle)
    summed = sum(fixed_pair(weights, u, v)[1] for u, v in combinations(range(4), 2))
    expanded = add_paths(cycle, 0, 2, 4)
    if (sum(relevant_histogram(weights).values()), summed,
            sum(relevant_histogram(edge_weights_by_shore(expanded)).values())) != (6, 20, 70):
        raise AssertionError("four-cycle example")
    triangle_with_leaf = Graph(4, ((0, 1), (0, 2), (0, 3), (1, 2)))
    small, _ = quotient(triangle_with_leaf, [(1, 3)])
    expanded = add_paths(triangle_with_leaf, 1, 3, 1)
    if (sum(relevant_histogram(edge_weights_by_shore(small)).values()),
            sum(relevant_histogram(edge_weights_by_shore(expanded)).values())) != (3, 10):
        raise AssertionError("below-threshold example")
    # Full restricted reductions, including a multigraph and an output of girth eight.
    for multiplicity, length, expected in ((2, 2, 70), (1, 4, 4132)):
        original = Graph(2, ((0, 1),) * multiplicity)
        divided = subdivision(original, length)
        expanded = add_paths(divided, 0, 1, divided.n, length)
        actual = sum(relevant_histogram(edge_weights_by_shore(expanded)).values())
        intervals = divided.n * length * (length - 1) // 2
        decoded = (actual - intervals) // length ** (divided.n + multiplicity)
        if actual != expected or decoded != 1:
            raise AssertionError(("restricted example", multiplicity, length, actual))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-order", type=int, choices=range(2, 7), default=6)
    args = parser.parse_args()
    check_worked_examples()
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(["order", "graphs", "terminal_pairs", "tree_orders", "long_path_pairs", "composed_pairs"])
    for n in range(2, args.max_order + 1):
        writer.writerow(check_order(n))


if __name__ == "__main__":
    main()
