"""JSON-safe multi-junction observations aggregated from one SUMO connection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from Ai.common.traffic_state import IntersectionState, SumoSensorReader


@dataclass
class NetworkState:
    """One simulation snapshot containing every intended TLS state."""

    sim_time: float
    junctions: dict[str, IntersectionState]
    totals: dict[str, int | float]

    def to_dict(self) -> dict[str, Any]:
        """Convert the snapshot to built-in JSON-serializable values."""
        return {
            "sim_time": float(self.sim_time),
            "junctions": {tls_id: state.to_dict() for tls_id, state in self.junctions.items()},
            "totals": {key: float(value) for key, value in self.totals.items()},
        }


class NetworkSensorReader:
    """Read each intended TLS with the existing, tested single-TLS sensor."""

    def __init__(
        self,
        tls_configs: list[Mapping[str, Any]],
        thresholds: Mapping[str, int] | None = None,
    ) -> None:
        if not tls_configs:
            raise ValueError("at least one intended TLS configuration is required")
        ids = [str(item["tls_id"]) for item in tls_configs]
        if len(ids) != len(set(ids)):
            raise ValueError("TLS configuration IDs must be unique")
        self.readers = {
            str(item["tls_id"]): SumoSensorReader(item, thresholds)
            for item in tls_configs
        }

    def read(self, client: Any) -> NetworkState:
        """Read all junctions from the same TraCI tick and aggregate totals."""
        junctions = {tls_id: reader.read(client) for tls_id, reader in self.readers.items()}
        totals: dict[str, int | float] = {
            "vehicle_count": 0,
            "halting": 0,
            "queue_length": 0.0,
            "avg_wait": 0.0,
            "throughput_veh_min": 0.0,
        }
        wait_sum = 0.0
        wait_count = 0
        for state in junctions.values():
            for approach in state.approaches:
                totals["vehicle_count"] += int(approach.vehicle_count or 0)
                totals["halting"] += int(approach.halting or 0)
                totals["queue_length"] += float(approach.queue_length or 0.0)
            totals["throughput_veh_min"] += float(state.totals.get("throughput_veh_min", 0.0))
            wait_sum += float(state.totals.get("avg_wait", 0.0)) * int(state.totals.get("waiting_vehicles", 0))
            wait_count += int(state.totals.get("waiting_vehicles", 0))
        totals["avg_wait"] = wait_sum / wait_count if wait_count else 0.0
        return NetworkState(
            sim_time=max((state.sim_time for state in junctions.values()), default=0.0),
            junctions=junctions,
            totals=totals,
        )
