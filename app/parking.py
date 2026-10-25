from dataclasses import dataclass
from datetime import datetime, timezone
from math import cos
from math import hypot
from math import isfinite
from math import radians
import re
from threading import Lock
from typing import Dict
from typing import List
from typing import Optional

from app.navigation import NavNode
from app.navigation import NavigationGraph
from app.navigation import build_route_steps


@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


@dataclass(frozen=True)
class ParkingSpot:
    id: str
    level: str
    zone: str
    number: str
    status: str
    kind: str
    offset_east_m: float
    offset_north_m: float
    landmark: str

    @property
    def label(self) -> str:
        return f"{self.level} 层 {self.zone} 区 {self.number} 号"


class ParkingRepository:
    """In-memory parking spot feed used by the demo parking lot."""

    def __init__(self, spots: List[ParkingSpot]):
        self._spots = list(spots)
        self._lock = Lock()

    def snapshot(self) -> List[ParkingSpot]:
        with self._lock:
            return list(self._spots)


DEMO_ENTRANCE = Coordinates(
    latitude=31.230600,
    longitude=121.473700,
)

DEMO_SPOTS = [
    ParkingSpot("B1-A-018", "B1", "A", "018", "available", "standard", 22, 14, "A 区电梯厅旁"),
    ParkingSpot("B1-A-021", "B1", "A", "021", "available", "standard", 30, 20, "A 区电梯厅附近"),
    ParkingSpot("B1-B-012", "B1", "B", "012", "available", "standard", 52, 18, "B 区服务台旁"),
    ParkingSpot("B1-C-009", "B1", "C", "009", "available", "standard", 72, 33, "C 区出口附近"),
    ParkingSpot("B1-A-001", "B1", "A", "001", "occupied", "accessible", 5, 5, "无障碍车位"),
    ParkingSpot("B1-B-006", "B1", "B", "006", "occupied", "standard", 44, 12, "B 区中部"),
    ParkingSpot("B1-C-003", "B1", "C", "003", "occupied", "standard", 61, 25, "C 区入口"),
    ParkingSpot("B2-A-031", "B2", "A", "031", "reserved", "standard", 16, 35, "A 区电梯厅附近"),
    ParkingSpot("B2-A-035", "B2", "A", "035", "available", "standard", 26, 42, "A 区充电区旁"),
    ParkingSpot("B2-B-014", "B2", "B", "014", "available", "standard", 50, 30, "B 区服务台附近"),
    ParkingSpot("B2-C-008", "B2", "C", "008", "occupied", "standard", 68, 41, "C 区出口附近"),
    ParkingSpot("B2-C-021", "B2", "C", "021", "occupied", "standard", 77, 36, "C 区中部"),
    ParkingSpot("B3-A-002", "B3", "A", "002", "available", "standard", 14, 58, "A 区电梯厅旁"),
    ParkingSpot("B3-B-020", "B3", "B", "020", "available", "standard", 64, 48, "B 区长停车区"),
    ParkingSpot("B3-C-011", "B3", "C", "011", "occupied", "standard", 81, 52, "C 区出口附近"),
]


def _normalize_spot_reference(value: str) -> str:
    """Normalize spoken spot references such as "B2 区 A 035 号"."""
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def find_parking_spot_id(
    text: str,
    spots: Optional[List[ParkingSpot]] = None,
) -> Optional[str]:
    """Return a unique spot ID mentioned in natural speech or text."""
    normalized_question = _normalize_spot_reference(text)
    if not normalized_question:
        return None

    candidates = list(spots or DEMO_SPOTS)
    full_matches = [
        spot.id
        for spot in candidates
        if _normalize_spot_reference(spot.id) in normalized_question
    ]
    if len(full_matches) == 1:
        return full_matches[0]

    # Accept shorthand such as "A035" when the zone/number is unique.
    short_matches = [
        spot.id
        for spot in candidates
        if _normalize_spot_reference(
            f"{spot.zone}{spot.number}"
        ) in normalized_question
    ]
    if len(short_matches) == 1:
        return short_matches[0]

    return None


class ParkingService:
    """Expose live demo availability and find the nearest suitable spot."""

    USER_LOCATION_MAX_DISTANCE_M = 500

    def __init__(self):
        self.lot_id = "navpark-xinghe-001"
        self.name = "NavPark 星河中心停车场（演示）"
        self.address = "上海市黄浦区星河路 88 号 B1–B3（虚构地点）"
        self.entrance = DEMO_ENTRANCE
        self.repository = ParkingRepository(DEMO_SPOTS)

    def get_availability(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict:
        spots = self.repository.snapshot()
        origin, location_info = self._resolve_origin(latitude, longitude)
        ranked, routes_by_spot = self._plan_routes(
            spots,
            origin,
            location_info,
        )

        levels = sorted({spot.level for spot in spots})
        by_level = {}
        for level in levels:
            level_spots = [spot for spot in spots if spot.level == level]
            by_level[level] = {
                "available": sum(
                    1
                    for spot in level_spots
                    if spot.status == "available"
                ),
                "total": len(level_spots),
            }

        nearest_spot = ranked[0] if ranked else None
        navigation = None
        if nearest_spot:
            selected_route = routes_by_spot[nearest_spot["id"]]
            nearest_spot = dict(nearest_spot)
            nearest_spot["route"] = selected_route
            nearest_spot["navigation_hint"] = self._navigation_hint(
                nearest_spot["level"],
                selected_route["steps"],
            )
            navigation = selected_route

        return {
            "lot": {
                "id": self.lot_id,
                "name": self.name,
                "address": self.address,
                "entrance": self.entrance.to_dict(),
            },
            "generated_at": datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
            "is_demo_data": True,
            "counts": {
                "available": len(ranked),
                "total": len(spots),
                "by_level": by_level,
            },
            "location": location_info,
            "available_spots": ranked[:5],
            "nearest_spot": nearest_spot,
            "navigation": navigation,
        }

    def get_route(
        self,
        spot_id: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict:
        spots = self.repository.snapshot()
        origin, location_info = self._resolve_origin(latitude, longitude)
        _, routes_by_spot = self._plan_routes(
            spots,
            origin,
            location_info,
        )

        if not routes_by_spot:
            raise ValueError("当前没有可导航的可用标准车位。")

        selected_id = spot_id
        if selected_id is None:
            selected_id = min(
                routes_by_spot,
                key=lambda key: routes_by_spot[key]["distance_m"],
            )

        if selected_id not in routes_by_spot:
            raise ValueError(
                f"车位 {selected_id} 不存在、不可用或不是标准车位。"
            )
        return routes_by_spot[selected_id]

    def get_lot_map(self) -> Dict:
        """Return the live indoor map, lane network, and spot statuses."""
        spots = self.repository.snapshot()
        graph = self._build_navigation_graph(spots)
        levels = []

        for level in ("B1", "B2", "B3"):
            level_spots = [
                self._serialize_map_spot(spot)
                for spot in spots
                if spot.level == level
            ]
            level_spots.sort(key=lambda item: item["id"])
            level_nodes = [
                {
                    "id": node.id,
                    "label": node.label,
                    "kind": node.kind,
                    "x_m": node.x_m,
                    "y_m": node.y_m,
                }
                for node in graph.nodes.values()
                if node.level == level
                and node.kind in {"aisle", "ramp", "start"}
            ]
            level_nodes.sort(key=lambda item: item["id"])
            node_ids = {node["id"] for node in level_nodes}
            seen_edges = set()
            level_edges = []
            for node_id in sorted(node_ids):
                for edge in graph.edges_from(node_id):
                    destination = graph.nodes[edge.to_id]
                    if (
                        destination.id not in node_ids
                        or destination.level != level
                    ):
                        continue
                    edge_key = tuple(sorted((node_id, destination.id)))
                    if edge_key in seen_edges:
                        continue
                    seen_edges.add(edge_key)
                    level_edges.append({
                        "from": edge_key[0],
                        "to": edge_key[1],
                        "kind": edge.kind,
                        "distance_m": round(edge.distance_m, 1),
                    })

            levels.append({
                "id": level,
                "label": level,
                "counts": {
                    "available": sum(
                        1
                        for spot in level_spots
                        if spot["status"] == "available"
                    ),
                    "total": len(level_spots),
                },
                "nodes": level_nodes,
                "edges": sorted(
                    level_edges,
                    key=lambda item: (item["from"], item["to"]),
                ),
                "spots": level_spots,
            })

        return {
            "version": 1,
            "lot": {
                "id": self.lot_id,
                "name": self.name,
                "address": self.address,
                "entrance": self.entrance.to_dict(),
            },
            "generated_at": datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
            "is_demo_data": True,
            "refresh_after_seconds": 10,
            "bounds": {
                "east_min": -6,
                "east_max": 96,
                "north_min": -6,
                "north_max": 66,
            },
            "zones": [
                {
                    "id": "A",
                    "label": "A 区",
                    "east_min": 0,
                    "east_max": 40,
                    "north_min": 0,
                    "north_max": 54,
                },
                {
                    "id": "B",
                    "label": "B 区",
                    "east_min": 40,
                    "east_max": 62,
                    "north_min": 0,
                    "north_max": 54,
                },
                {
                    "id": "C",
                    "label": "C 区",
                    "east_min": 62,
                    "east_max": 86,
                    "north_min": 0,
                    "north_max": 54,
                },
                {
                    "id": "RAMP",
                    "label": "坡道",
                    "east_min": 86,
                    "east_max": 95,
                    "north_min": 0,
                    "north_max": 65,
                },
            ],
            "floor_links": [
                {
                    "from": "B1",
                    "to": "B2",
                    "x_m": 90,
                    "y_m": 44,
                    "label": "B1 坡道",
                },
                {
                    "from": "B2",
                    "to": "B3",
                    "x_m": 90,
                    "y_m": 44,
                    "label": "B2 坡道",
                },
            ],
            "levels": levels,
        }

    def _plan_routes(
        self,
        spots: List[ParkingSpot],
        origin: Coordinates,
        location_info: Dict,
    ):
        graph = self._build_navigation_graph(spots)
        start_id = self._navigation_start_node(
            graph,
            origin,
            location_info,
        )
        available = [
            spot
            for spot in spots
            if spot.status == "available" and spot.kind == "standard"
        ]
        ranked = []
        routes_by_spot = {}

        for spot in available:
            route_path = graph.shortest_path(
                start_id,
                f"spot:{spot.id}",
            )
            route = self._serialize_route(
                graph,
                route_path,
                spot,
            )
            spot_info = self._serialize_spot(spot, origin)
            spot_info["route_distance_m"] = route["distance_m"]
            spot_info["estimated_drive_seconds"] = route[
                "estimated_drive_seconds"
            ]
            ranked.append(spot_info)
            routes_by_spot[spot.id] = route

        ranked.sort(
            key=lambda item: (
                item["route_distance_m"],
                item["distance_m"],
                item["id"],
            )
        )
        return ranked, routes_by_spot

    def _build_navigation_graph(
        self,
        spots: List[ParkingSpot],
    ) -> NavigationGraph:
        graph = NavigationGraph()
        anchor_specs = (
            ("a_approach", 22, 7, "A 区入口通道"),
            ("a_north", 24, 20, "A 区中部通道"),
            ("a_far", 22, 36, "A 区北侧通道"),
            ("b_south", 50, 12, "B 区南侧通道"),
            ("b_north", 52, 28, "B 区中部通道"),
            ("b_far", 52, 44, "B 区北侧通道"),
            ("c_south", 70, 28, "C 区南侧通道"),
            ("c_north", 76, 37, "C 区北侧通道"),
            ("c_far", 80, 50, "C 区北侧通道"),
            ("ramp", 90, 44, "坡道与电梯口"),
        )
        edge_pairs = (
            ("a_approach", "a_north"),
            ("a_north", "a_far"),
            ("a_approach", "b_south"),
            ("b_south", "b_north"),
            ("b_north", "b_far"),
            ("b_south", "c_south"),
            ("c_south", "c_north"),
            ("c_north", "c_far"),
            ("c_far", "ramp"),
            ("a_far", "b_far"),
            ("b_far", "c_far"),
            ("a_north", "b_north"),
            ("b_north", "c_north"),
        )

        for level in ("B1", "B2", "B3"):
            graph.add_node(
                NavNode(
                    f"{level.lower()}-ramp",
                    level,
                    90,
                    44,
                    f"{level} 坡道",
                    "ramp",
                )
            )
            for anchor_id, east, north, label in anchor_specs:
                if anchor_id == "ramp":
                    continue
                graph.add_node(
                    NavNode(
                        f"{level.lower()}-{anchor_id}",
                        level,
                        east,
                        north,
                        f"{level} {label}",
                    )
                )
            for first, second in edge_pairs:
                graph.connect(
                    f"{level.lower()}-{first}",
                    f"{level.lower()}-{second}",
                )

        graph.add_node(
            NavNode(
                "b1-entry",
                "B1",
                0,
                0,
                "停车场入口",
                "start",
            )
        )
        graph.connect("b1-entry", "b1-a_approach", kind="entry")
        graph.connect(
            "b1-ramp",
            "b2-ramp",
            kind="ramp",
            distance_m=30,
        )
        graph.connect(
            "b2-ramp",
            "b3-ramp",
            kind="ramp",
            distance_m=30,
        )

        anchors_by_level = {}
        for node in graph.nodes.values():
            if node.kind != "aisle":
                continue
            anchors_by_level.setdefault(node.level, []).append(node)

        for spot in spots:
            spot_node = NavNode(
                f"spot:{spot.id}",
                spot.level,
                spot.offset_east_m,
                spot.offset_north_m,
                spot.label,
                "spot",
            )
            graph.add_node(spot_node)
            nearest_anchors = sorted(
                anchors_by_level[spot.level],
                key=lambda node: hypot(
                    node.x_m - spot.offset_east_m,
                    node.y_m - spot.offset_north_m,
                ),
            )[:2]
            for anchor in nearest_anchors:
                graph.connect(
                    spot_node.id,
                    anchor.id,
                    kind="spot_access",
                )

        return graph

    def _navigation_start_node(
        self,
        graph: NavigationGraph,
        origin: Coordinates,
        location_info: Dict,
    ) -> str:
        start_id = "b1-entry"
        if location_info["accepted"]:
            east, north = self._coordinates_to_offset(origin)
            inside_lot = -5 <= east <= 95 and -5 <= north <= 65
            if inside_lot:
                graph.add_node(
                    NavNode(
                        "user-start",
                        "B1",
                        east,
                        north,
                        "你的场内位置（按 B1 层估算）",
                        "start",
                    )
                )
                b1_anchors = [
                    node
                    for node in graph.nodes.values()
                    if node.level == "B1" and node.kind == "aisle"
                ]
                nearest_anchors = sorted(
                    b1_anchors,
                    key=lambda node: hypot(
                        node.x_m - east,
                        node.y_m - north,
                    ),
                )[:2]
                for anchor in nearest_anchors:
                    graph.connect(
                        "user-start",
                        anchor.id,
                        kind="location_access",
                    )
                start_id = "user-start"
                location_info["message"] = (
                    "已按浏览器定位导航；浏览器定位不包含楼层，"
                    "起点按 B1 层估算。"
                )
            else:
                location_info["message"] += (
                    " 定位点不在场内通道范围内，导航起点已改为停车场入口。"
                )

        start_node = graph.nodes[start_id]
        location_info["navigation_start"] = {
            "node_id": start_node.id,
            "label": start_node.label,
            "level": start_node.level,
            "level_assumed": start_node.id == "user-start",
        }
        return start_id

    def _serialize_route(
        self,
        graph: NavigationGraph,
        route_path,
        spot: ParkingSpot,
    ) -> Dict:
        nodes = [
            graph.nodes[node_id]
            for node_id in route_path.node_ids
        ]
        floor_changes = sum(
            1
            for origin, destination in zip(nodes, nodes[1:])
            if origin.level != destination.level
        )
        steps = build_route_steps(
            graph,
            route_path,
            spot.label,
        )
        estimated_seconds = round(
            route_path.distance_m / 2.5
            + floor_changes * 6
        )
        path = [
            {
                "node_id": node.id,
                "label": node.label,
                "level": node.level,
                "x_m": node.x_m,
                "y_m": node.y_m,
                "coordinates": self._local_to_coordinates(
                    node.x_m,
                    node.y_m,
                ).to_dict(),
            }
            for node in nodes
        ]

        return {
            "algorithm": "a_star",
            "selection": "minimum_route_distance",
            "generated_at": datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
            "is_demo_data": True,
            "refresh_after_seconds": 10,
            "start": path[0],
            "destination": {
                "spot_id": spot.id,
                "label": spot.label,
                "level": spot.level,
                "x_m": spot.offset_east_m,
                "y_m": spot.offset_north_m,
                "status": spot.status,
                "landmark": spot.landmark,
                "coordinates": self._spot_coordinates(spot).to_dict(),
            },
            "distance_m": round(route_path.distance_m, 1),
            "estimated_drive_seconds": estimated_seconds,
            "floor_changes": floor_changes,
            "nodes_explored": route_path.nodes_explored,
            "steps": steps,
            "path": path,
        }

    def _resolve_origin(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
    ):
        if latitude is None or longitude is None:
            return self.entrance, {
                "requested": False,
                "accepted": False,
                "source": "parking_entrance",
                "distance_to_entrance_m": None,
                "message": "未提供浏览器定位，已按停车场入口计算。",
            }

        if not (
            isfinite(latitude)
            and isfinite(longitude)
            and -90 <= latitude <= 90
            and -180 <= longitude <= 180
        ):
            return self.entrance, {
                "requested": True,
                "accepted": False,
                "source": "parking_entrance",
                "distance_to_entrance_m": None,
                "message": "定位坐标无效，已按停车场入口计算。",
            }

        user_location = Coordinates(latitude, longitude)
        entrance_distance = self._distance_m(
            user_location,
            self.entrance,
        )
        if entrance_distance <= self.USER_LOCATION_MAX_DISTANCE_M:
            return user_location, {
                "requested": True,
                "accepted": True,
                "source": "user_location",
                "distance_to_entrance_m": round(entrance_distance, 1),
                "message": "已按浏览器定位计算。",
            }

        return self.entrance, {
            "requested": True,
            "accepted": False,
            "source": "parking_entrance",
            "distance_to_entrance_m": round(entrance_distance, 1),
            "message": (
                f"当前定位距离停车场入口约 {entrance_distance / 1000:.1f} 公里，"
                "超出 500 米场内范围，已按入口计算。"
            ),
        }

    def _spot_coordinates(self, spot: ParkingSpot) -> Coordinates:
        return self._local_to_coordinates(
            spot.offset_east_m,
            spot.offset_north_m,
        )

    def _local_to_coordinates(
        self,
        east_m: float,
        north_m: float,
    ) -> Coordinates:
        latitude = self.entrance.latitude + north_m / 111_320
        longitude = (
            self.entrance.longitude
            + east_m
            / (111_320 * cos(radians(self.entrance.latitude)))
        )
        return Coordinates(latitude, longitude)

    def _coordinates_to_offset(
        self,
        coordinates: Coordinates,
    ):
        north_m = (
            coordinates.latitude - self.entrance.latitude
        ) * 111_320
        east_m = (
            coordinates.longitude - self.entrance.longitude
        ) * 111_320 * cos(radians(self.entrance.latitude))
        return east_m, north_m

    def _serialize_spot(
        self,
        spot: ParkingSpot,
        origin: Coordinates,
    ) -> Dict:
        coordinates = self._spot_coordinates(spot)
        return {
            "id": spot.id,
            "label": spot.label,
            "level": spot.level,
            "zone": spot.zone,
            "number": spot.number,
            "status": spot.status,
            "kind": spot.kind,
            "landmark": spot.landmark,
            "distance_m": round(
                self._distance_m(origin, coordinates),
                1,
            ),
            "coordinates": coordinates.to_dict(),
        }

    def _serialize_map_spot(self, spot: ParkingSpot) -> Dict:
        coordinates = self._spot_coordinates(spot)
        return {
            "id": spot.id,
            "label": spot.label,
            "level": spot.level,
            "zone": spot.zone,
            "number": spot.number,
            "status": spot.status,
            "kind": spot.kind,
            "landmark": spot.landmark,
            "x_m": spot.offset_east_m,
            "y_m": spot.offset_north_m,
            "coordinates": coordinates.to_dict(),
        }

    def _navigation_hint(
        self,
        level: str,
        steps: List[Dict],
    ) -> str:
        return f"{level} 层 A* 推荐路线，共 {len(steps)} 个导航步骤。"

    @staticmethod
    def _distance_m(
        origin: Coordinates,
        destination: Coordinates,
    ) -> float:
        """Calculate great-circle distance using the haversine formula."""
        from math import asin, sqrt

        earth_radius_m = 6_371_000
        lat1 = radians(origin.latitude)
        lat2 = radians(destination.latitude)
        delta_lat = lat2 - lat1
        delta_lon = radians(
            destination.longitude - origin.longitude
        )
        value = (
            asin(
                sqrt(
                    (1 - cos(delta_lat)) / 2
                    + cos(lat1)
                    * cos(lat2)
                    * (1 - cos(delta_lon))
                    / 2
                )
            )
            * 2
        )
        return earth_radius_m * value


parking_service = ParkingService()
