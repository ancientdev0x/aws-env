import networkx as nx

def evaluate_reachability(nodes, edges, habitations, destinations, blocked_edges):
    G = nx.Graph()
    for u, v, w, eid in edges:
        if eid not in blocked_edges:
            G.add_edge(u, v, weight=w, edge_id=eid)
    
    results = {}
    for hab_id, hab_node in habitations.items():
        connected_dest = None
        min_dist = float('inf')
        for dest_id, dest_node in destinations.items():
            if dest_node in G and nx.has_path(G, hab_node, dest_node):
                d = nx.shortest_path_length(G, hab_node, dest_node, weight='weight')
                if d < min_dist:
                    min_dist = d
                    connected_dest = dest_id
        
        results[hab_id] = {
            "status": "PATH_EXISTS" if connected_dest else "NO_MAPPED_ROAD_PATH",
            "nearest": connected_dest,
            "dist": min_dist if connected_dest else None
        }
    return results

def test_reachability_lifecycle():
    # Toy graph: Habitation A connected via Edge 1 to Junction J, Junction J connected via Edge 2 to Hospital H
    # Alternative path: Junction J connected via Edge 3 to North Hub N
    nodes = ["A", "J", "H", "N"]
    edges = [
        ("A", "J", 2.0, "e1"), # Road from Village A to Junction J
        ("J", "H", 3.0, "e2"), # Road from Junction J to Hospital H
        ("J", "N", 5.0, "e3"), # Rural road from Junction J to North Hub N
    ]
    habitations = {"Village_A": "A"}
    destinations = {"Hospital_H": "H"}

    # 1. Baseline: All roads open
    r1 = evaluate_reachability(nodes, edges, habitations, destinations, blocked_edges=set())
    assert r1["Village_A"]["status"] == "PATH_EXISTS"
    assert r1["Village_A"]["nearest"] == "Hospital_H"

    # 2. Flood cuts Edge 2 (J -> H)
    r2 = evaluate_reachability(nodes, edges, habitations, destinations, blocked_edges={"e2"})
    assert r2["Village_A"]["status"] == "NO_MAPPED_ROAD_PATH"
    assert r2["Village_A"]["nearest"] is None

    # 3. Officer adds North Hub N as an active Staging Base
    destinations_with_hub = {"Hospital_H": "H", "Relief_Hub_N": "N"}
    r3 = evaluate_reachability(nodes, edges, habitations, destinations_with_hub, blocked_edges={"e2"})
    assert r3["Village_A"]["status"] == "PATH_EXISTS"
    assert r3["Village_A"]["nearest"] == "Relief_Hub_N"

    # 4. Officer confirms Edge 2 is actually an elevated bridge (Force Clear e2)
    r4 = evaluate_reachability(nodes, edges, habitations, destinations, blocked_edges=set())
    assert r4["Village_A"]["status"] == "PATH_EXISTS"
    assert r4["Village_A"]["nearest"] == "Hospital_H"

    print("✓ All Reachability Lifecycle assertions passed!")

if __name__ == "__main__":
    test_reachability_lifecycle()
