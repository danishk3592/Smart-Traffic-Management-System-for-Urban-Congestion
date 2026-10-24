"""Shared definition of traffic-light-controlled route movements."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from itertools import pairwise
from typing import Any


def controlled_movements(net: Any, tls_id: str) -> list[dict[str, Any]]:
    """Return unique edge-to-edge movements controlled by a TLS and their link indices."""
    try:
        tls = net.getTLS(tls_id)
    except KeyError as exc:
        raise ValueError(f"Traffic light is not present in the SUMO network: {tls_id}") from exc

    links: dict[tuple[str, str], set[int]] = defaultdict(set)
    for link_index, link_groups in tls.getLinks().items():
        for group in link_groups:
            from_lane, to_lane = group[0], group[1]
            from_edge = from_lane.getEdge().getID()
            to_edge = to_lane.getEdge().getID()
            links[(from_edge, to_edge)].add(int(link_index))
    return [
        {
            "from_edge": from_edge,
            "to_edge": to_edge,
            "link_indices": sorted(indices),
        }
        for (from_edge, to_edge), indices in sorted(links.items())
    ]


def route_uses_controlled_movement(
    route_edges: Iterable[str], movements: Iterable[dict[str, Any]]
) -> bool:
    """Return whether any consecutive route edge pair is a controlled movement."""
    route = tuple(route_edges)
    controlled = {
        (str(movement["from_edge"]), str(movement["to_edge"])) for movement in movements
    }
    return any(pair in controlled for pair in pairwise(route))
