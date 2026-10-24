"""Controller factory and SUMO-derived phase-to-approach mapping."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from Ai.common.config import load_config
from Ai.common.sumo_client import SumoClient
from Ai.controllers.base import Controller
from Ai.controllers.fallback import FallbackController
from Ai.controllers.fixed_time import FixedTimeController
from Ai.controllers.rule_based import RuleBasedController


def phase_approaches_from_network(
    net: Any, tls_config: Mapping[str, Any], program_id: str | None = None
) -> dict[int, tuple[str, ...]]:
    """Map each verified green phase to approaches using actual TLS link states."""
    tls_id = str(tls_config["tls_id"])
    tls = net.getTLS(tls_id)
    programs = tls.getPrograms()
    if program_id is None:
        if len(programs) != 1:
            raise ValueError(f"TLS {tls_id} needs an explicit program id; found {sorted(programs)}")
        program_id = next(iter(programs))
    if program_id not in programs:
        raise ValueError(f"TLS {tls_id} has no inspected program {program_id!r}")
    phases = programs[program_id].getPhases()
    result: dict[int, tuple[str, ...]] = {}
    for phase_index in tls_config["green_phases"]:
        phase = int(phase_index)
        if phase < 0 or phase >= len(phases):
            raise ValueError(f"TLS program {program_id} has no phase {phase}")
        served: set[str] = set()
        for approach in tls_config["approaches"]:
            lane_ids = set(approach.get("lanes", ()))
            edge_id = str(approach.get("incoming_edge", ""))
            for link_index, groups in tls.getLinks().items():
                if link_index >= len(phases[phase].state):
                    raise ValueError(f"TLS link index {link_index} exceeds phase state width")
                if phases[phase].state[link_index] not in "Gg":
                    continue
                if any(
                    group[0].getID() in lane_ids or group[0].getEdge().getID() == edge_id
                    for group in groups
                ):
                    served.add(str(approach["name"]))
        result[phase] = tuple(sorted(served))
    return result


def get_controller(
    name: str,
    project_config: Mapping[str, Any] | None = None,
    *,
    tls_config: Mapping[str, Any] | None = None,
) -> Controller:
    """Build a configured fixed or rule policy; RL arrives with T2.4."""
    config = dict(project_config or load_config())
    if tls_config is None:
        tls = dict(config["intersection"])
        tls["tls_id"] = str(config["sumo"]["tls_id"])
    else:
        tls = dict(tls_config)
    fixed = FixedTimeController(tls, float(config["fixed"]["green_s"]))
    key = name.lower()
    if key == "fixed":
        return fixed
    if key == "rule":
        client = SumoClient()
        net = client._resolve_config()["net"]
        phase_map = phase_approaches_from_network(net, tls)
        rule_config = config["rule"]
        controller = RuleBasedController(
            tls,
            phase_map,
            queue_threshold=int(rule_config["queue_threshold"]),
            wait_threshold_s=float(rule_config["wait_threshold_s"]),
            min_green_s=float(config["signal"]["min_green_s"]),
            max_green_s=float(config["signal"]["max_green_s"]),
            decision_interval_s=float(config["rl"]["decision_interval_s"]),
        )
        return FallbackController(controller, fixed)
    if key == "rl":
        raise NotImplementedError("RL controller is introduced by roadmap task T2.4")
    raise ValueError(f"Unknown controller {name!r}; choose fixed, rule, or rl")
