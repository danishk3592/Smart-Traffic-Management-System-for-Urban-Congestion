"""Safe, labelled TraCI sessions for the project SUMO configuration."""

from __future__ import annotations

import copy
import logging
import re
import shutil
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import sumolib
import traci
from sumolib.miscutils import getFreeSocketPort

logger = logging.getLogger(__name__)


class SumoClient:
    """Own one SUMO process and TraCI connection, with outputs outside source maps."""

    def __init__(
        self,
        config_path: str | Path | None = None,
        *,
        gui: bool = False,
        seed: int = 1000,
        label: str | None = None,
        repo_root: str | Path | None = None,
        route_file: str | Path | None = None,
        extra_additional_files: tuple[str | Path, ...] = (),
    ) -> None:
        root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
        self.config_path = (
            Path(config_path).expanduser().resolve()
            if config_path
            else (root / "config" / "stms.yaml")
        )
        self.gui = gui
        self.seed = int(seed)
        self.label = label or f"stms_{uuid.uuid4().hex[:12]}"
        self._repo_root = root
        self.route_file = Path(route_file).expanduser().resolve() if route_file else None
        self.extra_additional_files = tuple(Path(item).expanduser().resolve() for item in extra_additional_files)
        self._connection: Any = None
        self._process: Any = None
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self.sumo_output = ""
        self.tripinfo_output = ""
        self._started = False
        self._resolved: dict[str, Any] | None = None

    def __enter__(self) -> SumoClient:
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        self.close()
        return False

    @property
    def connection(self) -> Any:
        """Return this session's TraCI connection, raising if it is not active."""
        if self._connection is None:
            raise RuntimeError("SUMO client is not started")
        return self._connection

    @property
    def sim_time(self) -> float:
        """Return current simulation time in seconds."""
        return float(self.connection.simulation.getTime())

    @property
    def net(self) -> Any:
        """Return the validated sumolib network loaded before process startup."""
        if self._resolved is None:
            raise RuntimeError("SUMO network is unavailable before configuration validation")
        return self._resolved["net"]

    def _resolve_config(self) -> dict[str, Any]:
        import yaml

        with self.config_path.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
        if not isinstance(data, dict) or not isinstance(data.get("sumo"), dict):
            raise TypeError(f"Invalid SUMO configuration: {self.config_path}")

        value = data["sumo"].get("config")
        if not isinstance(value, str) or not value:
            raise ValueError("Configuration must define sumo.config")
        sumo_config = Path(value)
        if not sumo_config.is_absolute():
            sumo_config = self._repo_root / sumo_config
        sumo_config = sumo_config.resolve()
        if not sumo_config.is_file():
            raise FileNotFoundError(f"SUMO config file not found: {sumo_config}")

        xml_root = ET.parse(sumo_config).getroot()
        input_node = xml_root.find("input")
        if input_node is None:
            raise ValueError(f"SUMO config has no input section: {sumo_config}")

        files: dict[str, list[Path]] = {}
        for key in ("net-file", "route-files", "additional-files"):
            node = input_node.find(key)
            # SUMO's list-valued file attributes use commas/semicolons. Spaces
            # are valid within Windows paths and must not split a single file.
            values = [
                value.strip()
                for value in re.split(r"[,;]+", node.get("value", ""))
                if value.strip()
            ] if node is not None else []
            paths = []
            for item in filter(None, values):
                path = Path(item)
                if not path.is_absolute():
                    path = sumo_config.parent / path
                path = path.resolve()
                if not path.is_file():
                    raise FileNotFoundError(f"SUMO {key} file not found: {path}")
                paths.append(path)
            if key in {"net-file", "route-files"} and not paths:
                raise ValueError(f"SUMO config must define {key}: {sumo_config}")
            files[key] = paths

        net = sumolib.net.readNet(str(files["net-file"][0]), withPrograms=True)
        for route_file in files["route-files"]:
            ET.parse(route_file)
        for additional_file in files["additional-files"]:
            ET.parse(additional_file)
        for additional_file in self.extra_additional_files:
            if not additional_file.is_file():
                raise FileNotFoundError(f"Additional SUMO file not found: {additional_file}")
            ET.parse(additional_file)

        return {
            "sumo_config": sumo_config,
            "files": files,
            "net": net,
            "seed": self.seed,
        }

    def start(self) -> None:
        """Validate inputs and start one headless or GUI SUMO process."""
        if self._started:
            return
        self._resolved = self._resolve_config()
        if self.route_file is not None:
            if not self.route_file.is_file():
                raise FileNotFoundError(f"Scenario route file not found: {self.route_file}")
            ET.parse(self.route_file)
        executable = shutil.which("sumo-gui" if self.gui else "sumo")
        if executable is None:
            name = "sumo-gui" if self.gui else "sumo"
            raise FileNotFoundError(f"{name} executable is not available on PATH")

        self._temp_dir = tempfile.TemporaryDirectory(prefix="stms_sumo_")
        temp = Path(self._temp_dir.name)
        safe_additional = temp / "additional.xml"
        self._write_safe_additional(safe_additional)
        command = [
            executable,
            "-c",
            str(self._resolved["sumo_config"]),
            "--seed",
            str(self._resolved["seed"]),
            "--additional-files",
            str(safe_additional),
            "--tripinfo-output",
            str(temp / "tripinfo.xml"),
            "--tripinfo-output.write-unfinished",
            "--statistic-output",
            str(temp / "statistics.xml"),
            "--log",
            str(temp / "sumo.log"),
            "--duration-log.disable",
            "true",
            "--no-step-log",
            "true",
        ]
        if self.route_file is not None:
            command.extend(["--route-files", str(self.route_file)])
        port = getFreeSocketPort()
        try:
            traci.start(command, port=port, label=self.label, numRetries=10)
            self._connection = traci.getConnection(self.label)
            self._process = self._connection._process
            self._started = True
        except (traci.exceptions.TraCIException, OSError) as exc:
            self._stop_process()
            self._remove_temp()
            raise RuntimeError(f"Could not start SUMO/TraCI for {self.config_path}: {exc}") from exc

    def _write_safe_additional(self, destination: Path) -> None:
        """Copy configured additional elements while redirecting edge/lane output files."""
        root = ET.Element("additional")
        output_index = 0
        sources = [*self._resolved["files"]["additional-files"], *self.extra_additional_files]
        for source in sources:
            original = ET.parse(source).getroot()
            for child in original:
                safe_child = copy.deepcopy(child)
                for element in safe_child.iter():
                    if element.tag in {"edgeData", "laneData"} and element.get("file"):
                        output_index += 1
                        suffix = Path(element.get("file", "output.xml")).suffix or ".xml"
                        element.set("file", str(destination.parent / f"edge_data_{output_index}{suffix}"))
                root.append(safe_child)
        ET.ElementTree(root).write(destination, encoding="utf-8", xml_declaration=True)

    def step(self) -> None:
        """Advance one simulation step and raise a clear error if TraCI is lost."""
        try:
            self.connection.simulationStep()
        except (traci.exceptions.TraCIException, OSError, ConnectionError) as exc:
            self._stop_process()
            raise RuntimeError(f"TraCI connection was lost for SUMO label {self.label}: {exc}") from exc

    def close(self) -> None:
        """Close the TraCI socket and stop SUMO even if its connection was lost."""
        connection = self._connection
        if connection is not None:
            try:
                connection.close(wait=False)
            except (traci.exceptions.TraCIException, OSError, ConnectionError):
                logger.debug("TraCI close failed; stopping the SUMO process directly", exc_info=True)
        self._stop_process()
        if self._temp_dir is not None:
            log_path = Path(self._temp_dir.name) / "sumo.log"
            if log_path.is_file():
                self.sumo_output = log_path.read_text(encoding="utf-8", errors="replace")
            tripinfo_path = Path(self._temp_dir.name) / "tripinfo.xml"
            if tripinfo_path.is_file():
                self.tripinfo_output = tripinfo_path.read_text(encoding="utf-8", errors="replace")
        self._connection = None
        self._started = False
        self._remove_temp()

    def _stop_process(self) -> None:
        process = self._process
        if process is None:
            return
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        self._process = None

    def _remove_temp(self) -> None:
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None
