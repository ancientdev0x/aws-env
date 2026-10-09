"""
engine/reachability.py - BaadhDrishti Reachability & Triage Engine

Calculates habitation isolation and nearest destination using multi-source Dijkstra.
Strict rule: Blocked edges = (auto_suspected - force_cleared) | force_blocked
Excludes auto-disruption for bridge=yes edges (flags them as CHECK).
Handles INUNDATED status when habitation point is inside the flood mask.
"""

from typing import Dict, List, Set, Any, Optional
import networkx as nx

def evaluate_reachability(
    graph_edges: List[Dict[str, Any]],
    habitations: List[Dict[str, Any]],
    destinations: List[Dict[str, Any]],
    auto_suspected_edges: Set[str],
    force_cleared_edges: Optional[Set[str]] = None,
    force_blocked_edges: Optional[Set[str]] = None,
    inundated_habitations: Optional[Set[str]] = None
) -> List[Dict[str, Any]]:
    """
    Evaluates reachability for all habitations against a set of destinations.

    Args:
        graph_edges: List of edges with keys {'u', 'v', 'weight', 'edge_id', 'is_bridge'}
        habitations: List of habitations {'id', 'name', 'node', 'population_proxy', ...}
        destinations: List of destinations {'id', 'name', 'node', 'type', ...}
        auto_suspected_edges: Edge IDs intersecting flood mask (bridges excluded)
        force_cleared_edges: Edge IDs manually verified open by officer
        force_blocked_edges: Edge IDs manually marked blocked by officer
        inundated_habitations: Habitation IDs whose points fall inside flood mask

    Returns:
        List of habitation triage records sorted by status (INUNDATED > NO_MAPPED_ROAD_PATH > PATH_EXISTS)
        and then by population_proxy descending.
    """
    force_cleared = set(force_cleared_edges) if force_cleared_edges else set()
    force_blocked = set(force_blocked_edges) if force_blocked_edges else set()
    inundated = set(inundated_habitations) if inundated_habitations else set()

    # Rule 4: Bridges with bridge=yes / is_bridge=True must NOT be auto-disrupted.
    # Tag them with uncertainty flag CHECK.
    bridge_edges = {
        edge['edge_id'] for edge in graph_edges
        if edge.get('is_bridge') is True or str(edge.get('bridge', '')).lower() in ('yes', 'true')
    }
    for edge in graph_edges:
        if edge['edge_id'] in bridge_edges and edge['edge_id'] in auto_suspected_edges:
            edge['uncertainty_flag'] = 'CHECK'

    auto_blocked = set(auto_suspected_edges) - bridge_edges
    effective_blocked = (auto_blocked - force_cleared) | force_blocked

    # Build active graph
    G = nx.Graph()
    for edge in graph_edges:
        eid = edge['edge_id']
        if eid not in effective_blocked:
            G.add_edge(edge['u'], edge['v'], weight=edge.get('weight', 1.0), edge_id=eid)

    # Prepare destination mapping
    dest_node_to_id = {}
    valid_dest_nodes = set()
    for d in destinations:
        node = d['node']
        dest_node_to_id[node] = d
        if node in G:
            valid_dest_nodes.add(node)

    # Multi-source Dijkstra from all destinations simultaneously
    nearest_dist: Dict[Any, float] = {}
    nearest_dest_node: Dict[Any, Any] = {}
    if valid_dest_nodes:
        # When target is None, multi_source_dijkstra returns (dict[node, distance], dict[node, path])
        res = nx.multi_source_dijkstra(G, valid_dest_nodes, target=None, weight='weight')
        dist_dict: Dict[Any, float] = res[0]  # type: ignore
        path_dict: Dict[Any, List[Any]] = res[1]  # type: ignore

        for node, dist in dist_dict.items():
            nearest_dist[node] = float(dist)
            # path_dict[node] is a list of nodes starting at destination source and ending at node
            nearest_dest_node[node] = path_dict[node][0]

    # Evaluate each habitation
    triage_records = []
    for hab in habitations:
        hab_id = hab['id']
        hab_node = hab['node']
        is_inundated = hab_id in inundated

        if is_inundated:
            status = "INUNDATED"
        elif hab_node in nearest_dist:
            status = "PATH_EXISTS"
        else:
            status = "NO_MAPPED_ROAD_PATH"

        # Determine nearest destination details
        nearest_info = None
        if hab_node in nearest_dist:
            dest_node = nearest_dest_node[hab_node]
            dest_obj = dest_node_to_id.get(dest_node, {})
            nearest_info = {
                "id": dest_obj.get("id"),
                "name": dest_obj.get("name"),
                "type": dest_obj.get("type"),
                "distance_km": round(nearest_dist[hab_node], 2)
            }

        # Identify blocking edges connected directly or on incident edges
        blocking_edges = []
        if status in ("INUNDATED", "NO_MAPPED_ROAD_PATH"):
            for edge in graph_edges:
                if edge['edge_id'] in effective_blocked and (edge['u'] == hab_node or edge['v'] == hab_node):
                    blocking_edges.append(edge['edge_id'])

        uncertainty_flags = list(hab.get('uncertainty_flags', []))
        for edge in graph_edges:
            eid = edge['edge_id']
            if eid in bridge_edges and eid in auto_suspected_edges:
                if edge['u'] == hab_node or edge['v'] == hab_node:
                    if "CHECK" not in uncertainty_flags:
                        uncertainty_flags.append("CHECK")

        record = {
            **hab,
            "status": status,
            "nearest_destination": nearest_info,
            "blocking_edges": blocking_edges,
            "is_inundated": is_inundated,
            "uncertainty_flags": uncertainty_flags
        }
        triage_records.append(record)

    # Sort hierarchy: INUNDATED (0) > NO_MAPPED_ROAD_PATH (1) > PATH_EXISTS (2), then population descending
    status_order = {"INUNDATED": 0, "NO_MAPPED_ROAD_PATH": 1, "PATH_EXISTS": 2}
    triage_records.sort(
        key=lambda r: (
            status_order.get(r['status'], 3),
            -r.get('population_proxy', 0)
        )
    )

    return triage_records
