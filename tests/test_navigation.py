from app.navigation import NavNode
from app.navigation import NavigationGraph


def test_a_star_chooses_lowest_cost_path():
    graph = NavigationGraph()
    graph.add_node(NavNode("start", "B1", 0, 0, "start"))
    graph.add_node(NavNode("middle", "B1", 10, 0, "middle"))
    graph.add_node(NavNode("turn", "B1", 10, 10, "turn"))
    graph.add_node(NavNode("target", "B1", 20, 10, "target"))

    graph.connect("start", "target", distance_m=35)
    graph.connect("start", "middle", distance_m=10)
    graph.connect("middle", "turn", distance_m=10)
    graph.connect("turn", "target", distance_m=10)

    route = graph.shortest_path("start", "target")

    assert route.node_ids == ["start", "middle", "turn", "target"]
    assert route.distance_m == 30


def test_a_star_returns_path_through_floor_ramp():
    graph = NavigationGraph()
    graph.add_node(NavNode("b1-start", "B1", 0, 0, "B1 start"))
    graph.add_node(NavNode("b1-ramp", "B1", 10, 0, "B1 ramp"))
    graph.add_node(NavNode("b2-ramp", "B2", 10, 0, "B2 ramp"))
    graph.add_node(NavNode("b2-target", "B2", 20, 0, "B2 target"))

    graph.connect("b1-start", "b1-ramp", distance_m=10)
    graph.connect("b1-ramp", "b2-ramp", kind="ramp", distance_m=30)
    graph.connect("b2-ramp", "b2-target", distance_m=10)

    route = graph.shortest_path("b1-start", "b2-target")

    assert route.node_ids == ["b1-start", "b1-ramp", "b2-ramp", "b2-target"]
    assert route.distance_m == 50


def test_a_star_does_not_cut_through_another_parking_spot():
    graph = NavigationGraph()
    graph.add_node(NavNode("start", "B1", 0, 0, "start"))
    graph.add_node(NavNode("aisle-a", "B1", 0, 10, "aisle a"))
    graph.add_node(NavNode("aisle-b", "B1", 20, 10, "aisle b"))
    graph.add_node(NavNode("parked-car", "B1", 10, 10, "occupied", "spot"))
    graph.add_node(NavNode("target", "B1", 20, 0, "target", "spot"))

    graph.connect("start", "aisle-a", distance_m=10)
    graph.connect("aisle-a", "parked-car", distance_m=10)
    graph.connect("parked-car", "aisle-b", distance_m=10)
    graph.connect("aisle-b", "target", distance_m=10)
    graph.connect("aisle-a", "target", distance_m=35)

    route = graph.shortest_path("start", "target")

    assert "parked-car" not in route.node_ids
    assert route.distance_m == 45
