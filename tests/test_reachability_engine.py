"""
tests/test_reachability_engine.py

Unit and lifecycle tests for BaadhDrishti reachability & triage engine.
Tests all critical lifecycle cases:
1. Baseline open -> PATH_EXISTS to nearest hospital
2. Auto-suspected flood blocks edge -> NO_MAPPED_ROAD_PATH
3. Officer adds new Staging Hub -> PATH_EXISTS to new hub
4. Real FORCE_CLEARED override: edge in auto_suspected is present in force_cleared, so it stays open and status is PATH_EXISTS
5. Real FORCE_BLOCKED override: edge not flooded is manually force_blocked, so status becomes NO_MAPPED_ROAD_PATH
6. INUNDATED status: habitation point inside flood mask gets INUNDATED status and ranks #1 above other cut-off habitations
7. Bridge handling: OSM bridge=yes edge is NOT auto-disrupted and flagged with CHECK
"""

import sys
from pathlib import Path

# Ensure root workspace directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.reachability import evaluate_reachability


def test_reachability_engine():
    # Toy road network:
    # Habitation Village_A (pop 2,000) at node A -> Edge e1 (wt 2.0) -> Junction J
    # Habitation Village_B (pop 5,000) at node B -> Edge e4 (wt 1.0) -> Junction J
    # Junction J -> Edge e2 (wt 3.0) -> Hospital H
    # Junction J -> Edge e3 (wt 5.0) -> North Relief Hub N
    graph_edges = [
        {"u": "A", "v": "J", "weight": 2.0, "edge_id": "e1"},
        {"u": "J", "v": "H", "weight": 3.0, "edge_id": "e2"},
        {"u": "J", "v": "N", "weight": 5.0, "edge_id": "e3"},
        {"u": "B", "v": "J", "weight": 1.0, "edge_id": "e4"},
    ]

    hab_a = {"id": "Village_A", "name": "Village A", "node": "A", "population_proxy": 2000}
    hab_b = {"id": "Village_B", "name": "Village B", "node": "B", "population_proxy": 5000}
    dest_hospital = [{"id": "Hospital_H", "name": "Hospital H", "node": "H", "type": "HOSPITAL"}]

    # Case 1: Baseline open -> PATH_EXISTS to nearest hospital
    r1 = evaluate_reachability(
        graph_edges=graph_edges,
        habitations=[hab_a],
        destinations=dest_hospital,
        auto_suspected_edges=set()
    )
    assert len(r1) == 1
    assert r1[0]["status"] == "PATH_EXISTS"
    assert r1[0]["nearest_destination"]["id"] == "Hospital_H"
    assert r1[0]["nearest_destination"]["distance_km"] == 5.0
    print("✓ Case 1 passed: Baseline open -> PATH_EXISTS to nearest hospital")

    # Case 2: Auto-suspected flood blocks edge -> NO_MAPPED_ROAD_PATH
    r2 = evaluate_reachability(
        graph_edges=graph_edges,
        habitations=[hab_a],
        destinations=dest_hospital,
        auto_suspected_edges={"e2"}
    )
    assert len(r2) == 1
    assert r2[0]["status"] == "NO_MAPPED_ROAD_PATH"
    assert r2[0]["nearest_destination"] is None
    print("✓ Case 2 passed: Auto-suspected flood blocks edge -> NO_MAPPED_ROAD_PATH")

    # Case 3: Officer adds new Staging Hub -> PATH_EXISTS to new hub
    dest_with_hub = [
        {"id": "Hospital_H", "name": "Hospital H", "node": "H", "type": "HOSPITAL"},
        {"id": "Relief_Hub_N", "name": "Relief Hub N", "node": "N", "type": "STAGING_HUB"}
    ]
    r3 = evaluate_reachability(
        graph_edges=graph_edges,
        habitations=[hab_a],
        destinations=dest_with_hub,
        auto_suspected_edges={"e2"}
    )
    assert len(r3) == 1
    assert r3[0]["status"] == "PATH_EXISTS"
    assert r3[0]["nearest_destination"]["id"] == "Relief_Hub_N"
    assert r3[0]["nearest_destination"]["distance_km"] == 7.0
    print("✓ Case 3 passed: Officer adds new Staging Hub -> PATH_EXISTS to new hub")

    # Case 4: Real FORCE_CLEARED override: edge in auto_suspected is present in force_cleared,
    # so it stays open and status is PATH_EXISTS
    r4 = evaluate_reachability(
        graph_edges=graph_edges,
        habitations=[hab_a],
        destinations=dest_hospital,
        auto_suspected_edges={"e2"},
        force_cleared_edges={"e2"}
    )
    assert len(r4) == 1
    assert r4[0]["status"] == "PATH_EXISTS"
    assert r4[0]["nearest_destination"]["id"] == "Hospital_H"
    assert r4[0]["nearest_destination"]["distance_km"] == 5.0
    print("✓ Case 4 passed: Real FORCE_CLEARED override restores PATH_EXISTS")

    # Case 5: Real FORCE_BLOCKED override: edge not flooded is manually force_blocked,
    # so status becomes NO_MAPPED_ROAD_PATH
    r5 = evaluate_reachability(
        graph_edges=graph_edges,
        habitations=[hab_a],
        destinations=dest_hospital,
        auto_suspected_edges=set(),
        force_blocked_edges={"e2"}
    )
    assert len(r5) == 1
    assert r5[0]["status"] == "NO_MAPPED_ROAD_PATH"
    assert r5[0]["nearest_destination"] is None
    print("✓ Case 5 passed: Real FORCE_BLOCKED override triggers NO_MAPPED_ROAD_PATH")

    # Case 6: INUNDATED status: habitation point inside flood mask gets INUNDATED status
    # and ranks #1 above other cut-off habitations
    r6 = evaluate_reachability(
        graph_edges=graph_edges,
        habitations=[hab_a, hab_b],
        destinations=dest_hospital,
        auto_suspected_edges={"e2"},
        inundated_habitations={"Village_A"}
    )
    assert len(r6) == 2
    # Village_A is inundated
    assert r6[0]["id"] == "Village_A"
    assert r6[0]["status"] == "INUNDATED"
    # Village_B is cut-off but not inundated
    assert r6[1]["id"] == "Village_B"
    assert r6[1]["status"] == "NO_MAPPED_ROAD_PATH"
    # Crucial ranking assertion: Even though Village_B has larger population (5000 > 2000),
    # Village_A ranks #1 because INUNDATED > NO_MAPPED_ROAD_PATH
    assert r6[0]["population_proxy"] < r6[1]["population_proxy"]
    print("✓ Case 6 passed: INUNDATED status assigned and ranks #1 above other cut-off habitations")

    # Case 7: Bridge handling: OSM bridge=yes edges must NOT be auto-disrupted; tagged with CHECK
    bridge_graph_edges = [
        {"u": "A", "v": "J", "weight": 2.0, "edge_id": "e1"},
        {"u": "J", "v": "H", "weight": 3.0, "edge_id": "e_bridge", "is_bridge": True},
    ]
    r7 = evaluate_reachability(
        graph_edges=bridge_graph_edges,
        habitations=[hab_a],
        destinations=dest_hospital,
        auto_suspected_edges={"e_bridge"}
    )
    assert len(r7) == 1
    # Bridge is not auto-disrupted, path to hospital remains open
    assert r7[0]["status"] == "PATH_EXISTS"
    assert r7[0]["nearest_destination"]["id"] == "Hospital_H"
    # Bridge edge itself is tagged with CHECK
    bridge_edge_obj = next(e for e in bridge_graph_edges if e["edge_id"] == "e_bridge")
    assert bridge_edge_obj.get("uncertainty_flag") == "CHECK"
    print("✓ Case 7 passed: OSM bridge=yes edge not auto-disrupted and flagged CHECK")

    print("\n✓ All Reachability Engine assertions passed successfully!")


if __name__ == "__main__":
    test_reachability_engine()
