# Modified from https://nb.paulbutler.org/optimizing-plots-with-tsp-solver/

from collections import Counter
from typing import Iterable

import rtree
import shapely
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from tqdm import tqdm


def reverse_path(path: shapely.LineString) -> shapely.LineString:
    return shapely.ops.substring(path, 1, 0, normalized=True)


class PathGraph:
    # The origin is always at index 0.
    ORIGIN = 0

    def __init__(
            self, drawing: shapely.MultiLineString, origin: tuple[float, float] = (0, 0)
    ):
        """Constructs a PathGraph from the output of svgpathtools.svg2paths."""
        self.paths: list[shapely.LineString] = shapely.get_parts(drawing)
        # For any node i, endpoints[i] will be a pair containing that node's
        # start and end coordinates, respectively. For i==0 this represents
        # the origin.
        self.endpoints = [(origin, origin)]

        for path in self.paths:
            # For each path in the original list of paths,
            # create nodes for the path as well as its reverse.
            self.endpoints.append((path.coords[0], path.coords[-1]))
            self.endpoints.append((path.coords[-1], path.coords[0]))

    def get_path(self, i: int) -> shapely.LineString:
        """Returns the path corresponding to the node i."""
        index = (i - 1) // 2
        reverse = (i - 1) % 2
        path = self.paths[index]
        if reverse:
            return reverse_path(path)
        else:
            return path

    def cost(self, i: int, j: int):
        """Returns the distance between the end of path i
        and the start of path j."""
        return shapely.distance(
            shapely.Point(self.endpoints[i][1]), shapely.Point(self.endpoints[j][0])
        )

    def get_coordinates(self, i: int, end: bool = False) -> tuple[float, float]:
        """Returns the starting coordinates of node i as a pair,
        or the end coordinates iff end is True."""
        return self.endpoints[i][end]

    def iter_starts_with_index(self) -> Iterable[tuple[int, tuple[float, float]]]:
        """Returns a generator over (index, start coordinate) pairs,
        excluding the origin."""
        for i in range(1, len(self.endpoints)):
            yield i, self.get_coordinates(i)

    @staticmethod
    def get_disjoint(i) -> int:
        """For the node i, returns the index of the node associated with
        its path's opposite direction."""
        return ((i - 1) ^ 1) + 1

    def iter_disjunctions(self) -> Iterable[tuple[int, tuple[float, float]]]:
        """Returns a generator over 2-element lists of indexes which must
        be mutually exclusive in a solution (i.e. pairs of nodes which represent
        the same path in opposite directions.)"""
        for i in range(1, len(self.endpoints), 2):
            yield i, self.get_disjoint(i)

    def num_nodes(self):
        """Returns the number of nodes in the graph (including the origin.)"""
        return len(self.endpoints)

    def get_route_from_solution(self, solution: list[int]) -> shapely.MultiLineString:
        assert self.check_valid_solution(solution)
        return shapely.multilinestrings([self.get_path(i) for i in solution])

    def check_valid_solution(self, solution: list[int]):
        """Check that the solution is valid: every path is visited exactly once."""
        expected = Counter(
            i for (i, _) in self.iter_starts_with_index() if i < self.get_disjoint(i)
        )
        actual = Counter(min(i, self.get_disjoint(i)) for i in solution)
        difference = Counter(expected)
        difference.subtract(actual)
        difference = {k: v for k, v in difference.items() if v != 0}
        if difference:
            print(
                "Solution is not valid!"
                "Difference in node counts (expected - actual): {}".format(difference)
            )
            return False
        return True


class PathIndex:
    def __init__(self, path_graph: PathGraph):
        self.idx = rtree.index.Index()
        self.path_graph = path_graph
        for index, coordinate in path_graph.iter_starts_with_index():
            self.add(index, coordinate)

    def add(self, index: int, coordinate: tuple[float, float]):
        self.idx.add(index, coordinate + coordinate)

    def get_nearest(self, coordinate: tuple[float, float]) -> int:
        return next(self.idx.nearest(coordinate))

    def delete(self, index: int):
        coordinate = self.path_graph.get_coordinates(index)
        self.idx.delete(index, coordinate + coordinate)

    def delete_pair(self, index: int) -> None:
        self.delete(index)
        self.delete(self.path_graph.get_disjoint(index))

    def __len__(self):
        return len(self.idx)


def greedy_walk(
        path_graph: PathGraph, pbar: bool = True
) -> Iterable[int]:
    path_index = PathIndex(path_graph)
    location = path_graph.get_coordinates(path_graph.ORIGIN)
    bar = tqdm(
        total=len(path_index) // 2,
        disable=not pbar,
        leave=False,
    )
    while True:
        try:
            next_point = path_index.get_nearest(location)
        except StopIteration:
            break
        location = path_graph.get_coordinates(next_point, True)
        path_index.delete_pair(next_point)
        bar.update(1)
        yield next_point


def vrp_solver(path_graph: PathGraph, runtime_seconds: int = 60):
    """Solve a path using or-tools' Vehicle Routing Problem solver.
    Params:
        path_graph        the PathGraph representing the problem
        initial_solution  a solution to start with (list of indices, not
                          including the origin)
        runtime_seconds   how long to search before returning

    Returns: a (solution, curve) pair where the solution is a list of
        indices and the curve is a list of (clock seconds, best solution)
        pairs representing the progress of the solution over time.
    """
    # Create the VRP routing model. The 1 means we are only looking
    # for a single path.
    manager = pywrapcp.RoutingIndexManager(path_graph.num_nodes(), 1, path_graph.ORIGIN)
    routing = pywrapcp.RoutingModel(manager)

    # For every path node, add a disjunction so that we do not also
    # draw its reverse.
    for disjunction in path_graph.iter_disjunctions():
        routing.AddDisjunction(disjunction)

    # Wrap the distance function so that it converts to an integer,
    # as or-tools requires. Values are multiplied by COST_MULTIPLIER
    # prior to conversion to reduce the loss of precision.
    COST_MULTIPLIER = 1e4

    def distance(i, j) -> int:
        from_node = manager.IndexToNode(i)
        to_node = manager.IndexToNode(j)
        return int(path_graph.cost(from_node, to_node) * COST_MULTIPLIER)

    transit_callback_index = routing.RegisterTransitCallback(distance)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    if runtime_seconds is not None:
        search_parameters.time_limit.seconds = runtime_seconds

    solution = routing.SolveWithParameters(search_parameters)

    # Iterate over the result to produce a list to return as the solution.
    out = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        index = solution.Value(routing.NextVar(index))
        if index != 0 and index != path_graph.num_nodes():
            out.append(index)
    return out
