#!/usr/bin/env python3
"""
AHSER Waypoint Navigator
Command-line interface and ROS 2 Node for dispatching AHSER to named hospital waypoints.
"""

import argparse
import sys
import time
from typing import Optional

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose

# Support both installed package and direct script execution
try:
    from ahser_navigation.waypoint_manager import WaypointManager, Waypoint
except ImportError:
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from ahser_navigation.waypoint_manager import WaypointManager, Waypoint


class WaypointNavigator(Node):
    """ROS 2 Node that interfaces with Nav2 NavigateToPose action server."""

    def __init__(self, config_path: Optional[str] = None):
        super().__init__("ahser_waypoint_navigator")
        self.manager = WaypointManager(config_path)

        self._action_client = ActionClient(
            self,
            NavigateToPose,
            "/navigate_to_pose",
        )
        self._goal_handle = None
        self._last_feedback_time = 0.0

        self.get_logger().info(
            f"AHSER Waypoint Navigator initialized with {len(self.manager.get_names())} destinations from: {self.manager.config_path}"
        )

    def print_destinations(self) -> None:
        """Print a formatted table of all available destinations."""
        waypoints = self.manager.list_waypoints()
        print("\n" + "=" * 90)
        print(f" AHSER NAMED HOSPITAL DESTINATIONS ({len(waypoints)} locations)")
        print(f" Source Config: {self.manager.config_path}")
        print("=" * 90)
        print(f" {'NAME':<22} | {'FRAME':<6} | {'X (m)':<7} | {'Y (m)':<7} | {'YAW (rad)':<9} | {'DESCRIPTION'}")
        print("-" * 90)
        for wp in waypoints:
            print(
                f" {wp.name:<22} | {wp.frame_id:<6} | {wp.x:7.2f} | {wp.y:7.2f} | {wp.yaw:9.3f} | {wp.description}"
            )
        print("=" * 90 + "\n")

    def print_destination_info(self, name: str) -> None:
        """Print detailed information about a single destination."""
        wp = self.manager.get_waypoint(name)
        print("\n" + "-" * 50)
        print(f" Destination: {wp.name}")
        print(f" Description: {wp.description}")
        print(f" Coordinates: X = {wp.x:.3f} m, Y = {wp.y:.3f} m")
        print(f" Orientation: Yaw = {wp.yaw:.3f} rad ({wp.yaw * 180.0 / 3.14159265:.1f} deg)")
        print(f" Map Frame:   {wp.frame_id}")
        print("-" * 50 + "\n")

    def send_destination(self, name: str, server_timeout_sec: float = 5.0) -> bool:
        """
        Send AHSER to the named destination.
        Returns True if navigation succeeded, False if failed/cancelled.
        """
        # 1. Validate destination
        try:
            target_wp = self.manager.get_waypoint(name)
        except KeyError as e:
            self.get_logger().error(str(e))
            print(f"\n[ERROR] {e}\n", file=sys.stderr)
            return False

        self.get_logger().info(
            f"Target destination: '{target_wp.name}' at X={target_wp.x:.2f}, Y={target_wp.y:.2f}, Yaw={target_wp.yaw:.2f} ({target_wp.description})"
        )

        # 2. Wait for Nav2 action server
        self.get_logger().info("Connecting to Nav2 action server '/navigate_to_pose'...")
        if not self._action_client.wait_for_server(timeout_sec=server_timeout_sec):
            error_msg = (
                f"Nav2 action server '/navigate_to_pose' is not available after {server_timeout_sec:.1f}s. "
                "Ensure that the Nav2 navigation stack is running (e.g., ros2 launch ahser_navigation navigation.launch.py)."
            )
            self.get_logger().error(error_msg)
            print(f"\n[ERROR] {error_msg}\n", file=sys.stderr)
            return False

        # 3. Create Goal message
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = target_wp.to_pose_stamped(self.get_clock().now().to_msg())

        self.get_logger().info(f"Dispatching AHSER to '{name}'...")

        send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self._feedback_callback,
        )

        rclpy.spin_until_future_complete(self, send_goal_future)
        self._goal_handle = send_goal_future.result()

        if not self._goal_handle.accepted:
            self.get_logger().error(f"Nav2 rejected navigation goal for '{name}'!")
            print(f"\n[ERROR] Nav2 rejected goal for destination '{name}'!\n", file=sys.stderr)
            return False

        self.get_logger().info(f"Goal accepted by Nav2! AHSER is navigating to '{name}'...")

        # 4. Wait for navigation execution to complete
        result_future = self._goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result()

        status = result.status
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f"SUCCESS: AHSER reached destination '{name}'!")
            print(f"\n[SUCCESS] AHSER has arrived at '{name}' ({target_wp.description})!\n")
            return True
        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().warn(f"CANCELED: Navigation to '{name}' was canceled.")
            print(f"\n[WARNING] Navigation to '{name}' was canceled.\n", file=sys.stderr)
            return False
        elif status == GoalStatus.STATUS_ABORTED:
            self.get_logger().error(f"ABORTED: Navigation to '{name}' aborted by Nav2.")
            print(f"\n[ERROR] Navigation to '{name}' was aborted by Nav2 (path blocked or recovery failed).\n", file=sys.stderr)
            return False
        else:
            self.get_logger().error(f"Navigation to '{name}' ended with status code {status}.")
            print(f"\n[ERROR] Navigation ended with status {status}.\n", file=sys.stderr)
            return False

    def _feedback_callback(self, feedback_msg) -> None:
        """Periodic navigation feedback callback."""
        now = time.time()
        # Throttle log output to once every 2 seconds
        if now - self._last_feedback_time >= 2.0:
            fb = feedback_msg.feedback
            dist = fb.distance_remaining
            nav_time = fb.navigation_time.sec + fb.navigation_time.nanosec * 1e-9
            self.get_logger().info(
                f"Navigating... Distance remaining: {dist:.2f} m (Elapsed: {nav_time:.1f} s)"
            )
            self._last_feedback_time = now

    def cancel_active_goal(self) -> None:
        """Cancel current in-flight goal if active."""
        if self._goal_handle is not None:
            self.get_logger().info("Canceling active navigation goal...")
            future = self._goal_handle.cancel_goal_async()
            rclpy.spin_until_future_complete(self, future)


def main(args=None):
    parser = argparse.ArgumentParser(
        description="AHSER Named Hospital Waypoint Navigator CLI"
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to custom waypoints YAML file (default: searches package share / config)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List all configured hospital destinations and exit",
    )
    parser.add_argument(
        "--info",
        "-i",
        type=str,
        default=None,
        help="Display coordinate details for a specific destination",
    )
    parser.add_argument(
        "--goal",
        "-g",
        type=str,
        default=None,
        help="Name of destination to send AHSER to (e.g., medicine_station, nursing_station, patient_room_101)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch interactive graphical interface (Tkinter window)",
    )
    parser.add_argument(
        "--interactive",
        "-m",
        action="store_true",
        help="Launch interactive terminal selection menu (default when no args provided)",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=5.0,
        help="Timeout in seconds to connect to Nav2 action server (default: 5.0)",
    )

    cli_args, ros_args = parser.parse_known_args(args=args)

    # Launch GUI if requested
    if cli_args.gui:
        import subprocess
        gui_script = os.path.join(os.path.dirname(__file__), "waypoint_gui.py")
        if not os.path.exists(gui_script):
            # Fallback for installed location
            gui_script = "waypoint_gui"
        cmd = [sys.executable, gui_script] if gui_script.endswith(".py") else [gui_script]
        if cli_args.config:
            cmd.append(cli_args.config)
        try:
            sys.exit(subprocess.call(cmd))
        except Exception as e:
            print(f"[ERROR] Could not start GUI: {e}", file=sys.stderr)
            sys.exit(1)

    # Fast path for --list or --info: Does not require ROS 2 initialization if only inspecting
    if cli_args.list:
        try:
            manager = WaypointManager(cli_args.config)
            waypoints = manager.list_waypoints()
            print("\n" + "=" * 90)
            print(f" AHSER NAMED HOSPITAL DESTINATIONS ({len(waypoints)} locations)")
            print(f" Source Config: {manager.config_path}")
            print("=" * 90)
            print(f" {'NAME':<22} | {'FRAME':<6} | {'X (m)':<7} | {'Y (m)':<7} | {'YAW (rad)':<9} | {'DESCRIPTION'}")
            print("-" * 90)
            for wp in waypoints:
                print(
                    f" {wp.name:<22} | {wp.frame_id:<6} | {wp.x:7.2f} | {wp.y:7.2f} | {wp.yaw:9.3f} | {wp.description}"
                )
            print("=" * 90 + "\n")
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR] Failed to load waypoints: {e}", file=sys.stderr)
            sys.exit(1)

    if cli_args.info:
        try:
            manager = WaypointManager(cli_args.config)
            wp = manager.get_waypoint(cli_args.info)
            print("\n" + "-" * 50)
            print(f" Destination: {wp.name}")
            print(f" Description: {wp.description}")
            print(f" Coordinates: X = {wp.x:.3f} m, Y = {wp.y:.3f} m")
            print(f" Orientation: Yaw = {wp.yaw:.3f} rad ({wp.yaw * 180.0 / 3.14159265:.1f} deg)")
            print(f" Map Frame:   {wp.frame_id}")
            print("-" * 50 + "\n")
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)

    # Initialize ROS 2
    rclpy.init(args=ros_args)
    navigator = WaypointNavigator(config_path=cli_args.config)

    # Case A: Single goal CLI execution
    if cli_args.goal:
        try:
            success = navigator.send_destination(cli_args.goal, server_timeout_sec=cli_args.timeout)
        except KeyboardInterrupt:
            print("\n[INFO] Interrupt received, canceling goal...")
            navigator.cancel_active_goal()
            success = False
        finally:
            navigator.destroy_node()
            rclpy.shutdown()
        sys.exit(0 if success else 1)

    # Case B: Interactive Menu Selection Mode (Default when no flags passed)
    print("\n" + "=" * 80)
    print(" AHSER HOSPITAL DISPATCH INTERFACE")
    print("=" * 80)

    waypoints = navigator.manager.list_waypoints()
    # Numbered lookup mapping: 1 -> waypoint_name
    wp_map = {str(idx + 1): wp for idx, wp in enumerate(waypoints)}

    def print_menu():
        print("\n" + "-" * 80)
        print(" AVAILABLE HOSPITAL DESTINATIONS:")
        print("-" * 80)
        for idx, wp in enumerate(waypoints):
            print(f"  [{idx + 1:2d}] {wp.name:<22} - {wp.description}")
        print("-" * 80)
        print("  [ g] Launch Graphical Interface (GUI Window)")
        print("  [ q] Exit")
        print("-" * 80)

    print_menu()

    try:
        while rclpy.ok():
            try:
                choice = input("\n👉 Choose destination [1-15, name, 'g' for GUI, 'q' to quit]: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[INFO] Exiting AHSER dispatch interface. Goodbye!")
                break

            if not choice:
                continue

            if choice.lower() in ("q", "quit", "exit"):
                print("[INFO] Exiting AHSER dispatch interface. Goodbye!")
                break

            if choice.lower() in ("g", "gui"):
                print("[INFO] Launching graphical interface...")
                import subprocess
                gui_script = os.path.join(os.path.dirname(__file__), "waypoint_gui.py")
                if not os.path.exists(gui_script):
                    gui_script = "waypoint_gui"
                cmd = [sys.executable, gui_script] if gui_script.endswith(".py") else [gui_script]
                subprocess.Popen(cmd)
                continue

            if choice.lower() in ("m", "menu", "list", "help", "?"):
                print_menu()
                continue

            # Determine selected waypoint name
            target_name = None
            if choice in wp_map:
                target_name = wp_map[choice].name
            elif navigator.manager.has_waypoint(choice):
                target_name = choice
            else:
                # Try case-insensitive matching
                lower_map = {wp.name.lower(): wp.name for wp in waypoints}
                if choice.lower() in lower_map:
                    target_name = lower_map[choice.lower()]
                else:
                    try:
                        navigator.manager.get_waypoint(choice)
                    except KeyError as e:
                        print(f"[ERROR] {e}")
                    continue

            print(f"\n🚀 Sending AHSER to: '{target_name}'...")
            try:
                success = navigator.send_destination(target_name, server_timeout_sec=cli_args.timeout)
                if success:
                    print(f"✨ Ready for next destination! (Type 'm' to see list again, 'q' to quit)")
            except KeyboardInterrupt:
                print("\n[WARNING] Navigation interrupted! Canceling active goal...")
                navigator.cancel_active_goal()
                print("Goal canceled. AHSER is stopped.")

    finally:
        navigator.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    sys.exit(0)


if __name__ == "__main__":
    main()
