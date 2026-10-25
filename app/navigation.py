from dataclasses import dataclass
from heapq import heappop
from heapq import heappush
from itertools import count
from math import atan2
from math import degrees
from math import hypot
from math import pi
from typing import Dict
from typing import List
from typing import Optional


@dataclass(frozen=True)
class NavNode:
    id: str
    level: str
    x_m: float
    y_m: float
    label: str
    kind: str = "aisle"


@dataclass(frozen=True)
class NavEdge:
    to_id: str
    distance_m: float
    kind: str = "aisle"


@dataclass
class RoutePath:
    node_ids: List[str]
    distance_m: float
    nodes_explored: int


class NavigationGraph:
    """Weighted indoor navigation graph searched with A*."""

    RAMP_FLOOR_COST_M = 24.0

    def __init__(self):
        self._nodes: Dict[str, NavNode] = {}
        self._edges: Dict[str, List[NavEdge]] = {}

    @property
    def nodes(self) -> Dict[str, NavNode]:
        return dict(self._nodes)

    def add_node(self, node: NavNode) -> None:
        if node.id in self._nodes:
            raise ValueError(f"Duplicate navigation node: {node.id}")
        self._nodes[node.id] = node
        self._edges[node.id] = []

    def connect(
        self,
        from_id: str,
        to_id: str,
        kind: str = "aisle",
        distance_m: Optional[float] = None,
        bidirectional: bool = True,
    ) -> None:
        if from_id not in self._nodes or to_id not in self._nodes:
            raise KeyError("Both navigation nodes must exist before connecting")

        if distance_m is None:
            origin = self._nodes[from_id]
            destination = self._nodes[to_id]
            if origin.level != destination.level:
                raise ValueError("Cross-floor edges require an explicit distance")
            distance_m = hypot(
                destination.x_m - origin.x_m,
                destination.y_m - origin.y_m,
            )

        self._edges[from_id].append(NavEdge(to_id, distance_m, kind))
        if bidirectional:
            self._edges[to_id].append(NavEdge(from_id, distance_m, kind))

    def edges_from(self, node_id: str) -> List[NavEdge]:
        return list(self._edges.get(node_id, []))

    def shortest_path(self, start_id: str, target_id: str) -> RoutePath:
        if start_id not in self._nodes:
            raise KeyError(f"Unknown navigation start: {start_id}")
        if target_id not in self._nodes:
            raise KeyError(f"Unknown navigation destination: {target_id}")

        target = self._nodes[target_id]
        sequence = count()
        frontier = [
            (
                self._heuristic(self._nodes[start_id], target),
                0.0,
                next(sequence),
                start_id,
            )
        ]
        came_from = {}
        cost_so_far = {start_id: 0.0}
        nodes_explored = 0

        while frontier:
            _, current_cost, _, current_id = heappop(frontier)
            nodes_explored += 1

            if current_cost > cost_so_far.get(current_id, float("inf")):
                continue

            if current_id == target_id:
                node_ids = self._reconstruct_path(
                    came_from,
                    start_id,
                    target_id,
                )
                return RoutePath(
                    node_ids=node_ids,
                    distance_m=current_cost,
                    nodes_explored=nodes_explored,
                )

            if self._nodes[current_id].kind == "spot":
                # Parking spots are destinations, never through-lanes.
                continue

            for edge in self._edges[current_id]:
                next_cost = current_cost + edge.distance_m
                if next_cost >= cost_so_far.get(edge.to_id, float("inf")):
                    continue

                cost_so_far[edge.to_id] = next_cost
                came_from[edge.to_id] = current_id
                priority = next_cost + self._heuristic(
                    self._nodes[edge.to_id],
                    target,
                )
                heappush(
                    frontier,
                    (
                        priority,
                        next_cost,
                        next(sequence),
                        edge.to_id,
                    ),
                )

        raise ValueError(
            f"No navigation route from {start_id} to {target_id}"
        )

    @classmethod
    def _heuristic(cls, node: NavNode, target: NavNode) -> float:
        horizontal = hypot(
            target.x_m - node.x_m,
            target.y_m - node.y_m,
        )
        floor_distance = (
            abs(cls._level_number(target.level) - cls._level_number(node.level))
            * cls.RAMP_FLOOR_COST_M
        )
        return horizontal + floor_distance

    @staticmethod
    def _level_number(level: str) -> int:
        try:
            return int(level.lstrip("Bb"))
        except ValueError as exc:
            raise ValueError(f"Unsupported floor label: {level}") from exc

    @staticmethod
    def _reconstruct_path(
        came_from: Dict[str, str],
        start_id: str,
        target_id: str,
    ) -> List[str]:
        node_ids = [target_id]
        current_id = target_id
        while current_id != start_id:
            current_id = came_from[current_id]
            node_ids.append(current_id)
        node_ids.reverse()
        return node_ids


def build_route_steps(
    graph: NavigationGraph,
    route: RoutePath,
    destination_label: str,
) -> List[Dict]:
    """Convert graph nodes into concise turn-by-turn navigation steps."""
    nodes = [graph.nodes[node_id] for node_id in route.node_ids]
    if len(nodes) < 2:
        return [
            {
                "instruction": f"你已在 {destination_label} 附近。",
                "distance_m": 0.0,
                "level": nodes[0].level if nodes else None,
            }
        ]

    segments = []
    for origin, destination in zip(nodes, nodes[1:]):
        if origin.level != destination.level:
            origin_level = NavigationGraph._level_number(origin.level)
            destination_level = NavigationGraph._level_number(destination.level)
            direction = "下行" if destination_level > origin_level else "上行"
            segments.append(
                {
                    "kind": "ramp",
                    "distance_m": _find_edge_distance(
                        graph,
                        origin.id,
                        destination.id,
                    ),
                    "level": destination.level,
                    "action": f"沿坡道{direction}至 {destination.level}",
                    "start_label": destination.label,
                }
            )
            continue

        distance = hypot(
            destination.x_m - origin.x_m,
            destination.y_m - origin.y_m,
        )
        heading = atan2(
            destination.y_m - origin.y_m,
            destination.x_m - origin.x_m,
        )
        previous = segments[-1] if segments else None
        if (
            previous
            and previous["kind"] == "ground"
            and previous["level"] == destination.level
            and abs(
                _heading_difference(previous["heading"], heading)
            ) <= 0.52
        ):
            previous["distance_m"] += distance
        else:
            segments.append(
                {
                    "kind": "ground",
                    "level": destination.level,
                    "distance_m": distance,
                    "heading": heading,
                    "start_label": origin.label,
                }
            )

    steps = []
    previous_heading = None
    start_label = nodes[0].label
    for index, segment in enumerate(segments):
        is_final_segment = index == len(segments) - 1

        if segment["kind"] == "ramp":
            instruction = (
                f"{segment['action']}，约 {segment['distance_m']:.0f} 米"
            )
            if is_final_segment:
                instruction += f"，到达 {destination_label}"
            steps.append(
                {
                    "instruction": instruction,
                    "distance_m": round(segment["distance_m"], 1),
                    "level": segment["level"],
                }
            )
            start_label = segment["start_label"]
            previous_heading = None
            continue

        heading = segment["heading"]
        direction_name = _compass_direction(heading)
        if previous_heading is None:
            action = f"从 {start_label} 出发，向{direction_name}行驶"
        else:
            turn = _turn_direction(previous_heading, heading)
            if turn == "继续":
                action = f"继续向{direction_name}行驶"
            else:
                action = f"{turn}，向{direction_name}行驶"

        instruction = (
            f"{action}约 {segment['distance_m']:.0f} 米"
        )
        if is_final_segment:
            instruction += f"，到达 {destination_label}"
        steps.append(
            {
                "instruction": instruction,
                "distance_m": round(segment["distance_m"], 1),
                "level": segment["level"],
            }
        )
        previous_heading = heading

    return steps


def _find_edge_distance(
    graph: NavigationGraph,
    from_id: str,
    to_id: str,
) -> float:
    for edge in graph.edges_from(from_id):
        if edge.to_id == to_id:
            return edge.distance_m
    raise ValueError(f"Missing route edge: {from_id} -> {to_id}")


def _turn_direction(
    incoming_heading: float,
    outgoing_heading: float,
) -> str:
    difference = _heading_difference(
        incoming_heading,
        outgoing_heading,
    )
    difference_degrees = abs(degrees(difference))
    if difference_degrees <= 30:
        return "继续"
    if difference_degrees >= 150:
        return "掉头"
    return "向左转" if difference > 0 else "向右转"


def _heading_difference(
    incoming_heading: float,
    outgoing_heading: float,
) -> float:
    return (outgoing_heading - incoming_heading + pi) % (2 * pi) - pi


def _compass_direction(heading: float) -> str:
    directions = (
        "东",
        "东北",
        "北",
        "西北",
        "西",
        "西南",
        "南",
        "东南",
    )
    normalized = (degrees(heading) + 360) % 360
    index = int((normalized + 22.5) // 45) % 8
    return directions[index]
