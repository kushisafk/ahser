#!/usr/bin/env python3
"""
AHSER Waypoint Manager
Reusable module for loading, validating, and retrieving named hospital waypoints.
"""

import math
import os
import difflib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import yaml
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from ament_index_python.packages import get_package_share_directory, PackageNotFoundError


@dataclass
class Waypoint:
    name: str
    x: float
    y: float
    yaw: float
    frame_id: str = "map"
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "yaw": self.yaw,
            "frame_id": self.frame_id,
            "description": self.description,
        }

    def to_pose_stamped(self, clock_msg=None) -> PoseStamped:
        msg = PoseStamped()
        msg.header.frame_id = self.frame_id
        if clock_msg is not None:
            msg.header.stamp = clock_msg

        msg.pose.position.x = float(self.x)
        msg.pose.position.y = float(self.y)
        msg.pose.position.z = 0.0

        # Convert yaw to quaternion (rotation around Z axis)
        half_yaw = self.yaw / 2.0
        msg.pose.orientation.x = 0.0
        msg.pose.orientation.y = 0.0
        msg.pose.orientation.z = math.sin(half_yaw)
        msg.pose.orientation.w = math.cos(half_yaw)

        return msg


class UniqueKeyYamlLoader(yaml.SafeLoader):
    """YAML loader that detects duplicate keys in mappings and raises ValueError."""
    pass


def _construct_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(
                f"Duplicate waypoint name '{key}' detected in YAML at line {key_node.start_mark.line + 1}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


class WaypointManager:
    """Manages hospital destinations loaded from waypoints.yaml."""

    def __init__(self, config_path: Optional[str] = None):
        self._waypoints: Dict[str, Waypoint] = {}
        self._default_frame: str = "map"
        self._config_path: str = self._resolve_config_path(config_path)
        self.load_config(self._config_path)

    @staticmethod
    def _resolve_config_path(explicit_path: Optional[str]) -> str:
        """Find waypoints.yaml from explicit argument, package share, or source tree."""
        if explicit_path and os.path.exists(explicit_path):
            return os.path.abspath(explicit_path)

        # Try ROS 2 package share directory
        try:
            share_dir = get_package_share_directory("ahser_navigation")
            share_config = os.path.join(share_dir, "config", "waypoints.yaml")
            if os.path.exists(share_config):
                return share_config
        except PackageNotFoundError:
            pass

        # Try relative source directory in ahser_ws
        src_path = os.path.expanduser(
            "~/Desktop/ahser_ws/src/ahser_navigation/config/waypoints.yaml"
        )
        if os.path.exists(src_path):
            return os.path.abspath(src_path)

        # Fallback to local config directory relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_rel = os.path.join(current_dir, "..", "config", "waypoints.yaml")
        if os.path.exists(local_rel):
            return os.path.abspath(local_rel)

        if explicit_path:
            raise FileNotFoundError(f"Waypoints configuration file not found at: {explicit_path}")
        raise FileNotFoundError(
            "Could not locate waypoints.yaml in package share or source tree."
        )

    @property
    def config_path(self) -> str:
        return self._config_path

    @property
    def default_frame(self) -> str:
        return self._default_frame

    def load_config(self, filepath: str) -> None:
        """Load and validate waypoints configuration from a YAML file."""
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Configuration file does not exist: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=UniqueKeyYamlLoader)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML content in {filepath}: Expected a top-level mapping.")

        self._default_frame = data.get("frame_id", "map")
        raw_waypoints = data.get("waypoints", {})

        if not isinstance(raw_waypoints, dict):
            raise ValueError(f"'waypoints' key in {filepath} must be a dictionary mapping names to poses.")

        loaded_waypoints: Dict[str, Waypoint] = {}
        for name, entry in raw_waypoints.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Waypoint name must be a non-empty string, got: {name}")

            cleaned_name = name.strip()
            if not isinstance(entry, dict):
                raise ValueError(
                    f"Waypoint '{cleaned_name}' must be a mapping with x, y, and yaw coordinates."
                )

            # Validate coordinates
            for coord in ("x", "y", "yaw"):
                if coord not in entry:
                    raise KeyError(
                        f"Waypoint '{cleaned_name}' is missing required coordinate '{coord}'."
                    )
                val = entry[coord]
                if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                    raise ValueError(
                        f"Waypoint '{cleaned_name}' coordinate '{coord}' must be a valid finite number, got {val}."
                    )

            frame_id = entry.get("frame_id", self._default_frame)
            description = str(entry.get("description", ""))

            loaded_waypoints[cleaned_name] = Waypoint(
                name=cleaned_name,
                x=float(entry["x"]),
                y=float(entry["y"]),
                yaw=float(entry["yaw"]),
                frame_id=str(frame_id),
                description=description,
            )

        self._waypoints = loaded_waypoints
        self._config_path = filepath

    def get_names(self) -> List[str]:
        """Return a sorted list of all configured waypoint names."""
        return sorted(self._waypoints.keys())

    def has_waypoint(self, name: str) -> bool:
        """Check if a waypoint exists."""
        return name in self._waypoints

    def get_waypoint(self, name: str) -> Waypoint:
        """
        Look up a waypoint by name.
        Raises KeyError with helpful suggestion if not found.
        """
        if name in self._waypoints:
            return self._waypoints[name]

        # Provide helpful suggestions for typos
        available = self.get_names()
        suggestions = difflib.get_close_matches(name, available, n=3, cutoff=0.5)
        suggestion_str = (
            f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        )
        raise KeyError(
            f"Unknown waypoint '{name}'.{suggestion_str} Available waypoints: {available}"
        )

    def list_waypoints(self) -> List[Waypoint]:
        """Return all waypoints as a list."""
        return [self._waypoints[k] for k in self.get_names()]

    def to_pose_stamped(self, name: str, clock_msg=None) -> PoseStamped:
        """Retrieve a waypoint by name and convert to a PoseStamped message."""
        wp = self.get_waypoint(name)
        return wp.to_pose_stamped(clock_msg)

    def add_waypoint(
        self,
        name: str,
        x: float,
        y: float,
        yaw: float,
        frame_id: Optional[str] = None,
        description: str = "",
    ) -> None:
        """Programmatically register an additional waypoint in memory."""
        name = name.strip()
        if not name:
            raise ValueError("Waypoint name cannot be empty.")
        self._waypoints[name] = Waypoint(
            name=name,
            x=float(x),
            y=float(y),
            yaw=float(yaw),
            frame_id=frame_id or self._default_frame,
            description=description,
        )
