#!/usr/bin/env python3
"""
AHSER Waypoint GUI
Interactive graphical interface for selecting and dispatching AHSER to named hospital waypoints.
"""

import math
import os
import sys
import threading
import time
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose

# Support both installed package and direct script execution
try:
    from ahser_navigation.waypoint_manager import WaypointManager, Waypoint
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from ahser_navigation.waypoint_manager import WaypointManager, Waypoint


class Nav2BridgeNode(Node):
    """ROS 2 Node for handling Nav2 NavigateToPose in a background thread."""

    def __init__(self, waypoint_manager: WaypointManager):
        super().__init__("ahser_waypoint_gui_node")
        self.manager = waypoint_manager
        self._action_client = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self._current_goal_handle = None
        self._is_navigating = False

    def is_action_server_ready(self) -> bool:
        if not rclpy.ok():
            return False
        try:
            return self._action_client.server_is_ready()
        except Exception:
            return False

    def wait_for_server(self, timeout_sec: float = 2.0) -> bool:
        if not rclpy.ok():
            return False
        try:
            return self._action_client.wait_for_server(timeout_sec=timeout_sec)
        except Exception:
            return False

    def cancel_active_goal(self):
        if not rclpy.ok():
            return None
        if self._current_goal_handle is not None and self._is_navigating:
            self.get_logger().info("User requested goal cancellation.")
            try:
                return self._current_goal_handle.cancel_goal_async()
            except Exception:
                return None
        return None


class WaypointGUI:
    """Tkinter Graphical Dispatcher for AHSER Hospital Navigation."""

    def __init__(self, root: tk.Tk, config_path: Optional[str] = None):
        self.root = root
        self.root.title("AHSER — Hospital Destination Dispatcher")
        self.root.geometry("780x680")
        self.root.minsize(700, 600)

        # Set clean color palette
        self.bg_color = "#f4f6f9"
        self.card_bg = "#ffffff"
        self.accent_blue = "#1e40af"
        self.accent_green = "#15803d"
        self.accent_red = "#b91c1c"
        self.text_dark = "#0f172a"
        self.text_muted = "#475569"

        self.root.configure(bg=self.bg_color)

        # Load Waypoints
        self.manager = WaypointManager(config_path)

        # Initialize ROS 2 in background
        if not rclpy.ok():
            rclpy.init()
        self.ros_node = Nav2BridgeNode(self.manager)

        self._ros_thread = threading.Thread(target=self._spin_ros, daemon=True)
        self._ros_thread.start()

        # State tracking
        self.current_goal_name = None
        self.is_navigating = False
        self.destination_buttons = {}

        self._build_ui()
        self._check_nav2_connection()

    def _spin_ros(self):
        """Background thread spinning ROS 2 node."""
        while rclpy.ok():
            try:
                rclpy.spin_once(self.ros_node, timeout_sec=0.1)
            except Exception:
                break

    def _build_ui(self):
        """Construct the UI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="16 16 16 16")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Header ---
        header_frame = tk.Frame(main_frame, bg=self.card_bg, relief=tk.RIDGE, bd=1, padx=12, pady=10)
        header_frame.pack(fill=tk.X, pady=(0, 12))

        title_lbl = tk.Label(
            header_frame,
            text="🏥 AHSER Hospital Dispatch Manager",
            font=("Helvetica", 16, "bold"),
            bg=self.card_bg,
            fg=self.accent_blue,
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            header_frame,
            text="Autonomous Service Robot (Nav2) — Choose a destination below to dispatch AHSER",
            font=("Helvetica", 10),
            bg=self.card_bg,
            fg=self.text_muted,
        )
        subtitle_lbl.pack(anchor="w")

        # --- Status Banner ---
        self.status_frame = tk.Frame(
            main_frame, bg="#e2e8f0", relief=tk.SOLID, bd=1, padx=12, pady=10
        )
        self.status_frame.pack(fill=tk.X, pady=(0, 14))

        self.status_title = tk.Label(
            self.status_frame,
            text="STATUS: Checking Nav2 Action Server...",
            font=("Helvetica", 12, "bold"),
            bg="#e2e8f0",
            fg=self.text_dark,
        )
        self.status_title.pack(anchor="w")

        self.status_details = tk.Label(
            self.status_frame,
            text="Connecting to /navigate_to_pose action server...",
            font=("Helvetica", 10),
            bg="#e2e8f0",
            fg=self.text_muted,
        )
        self.status_details.pack(anchor="w")

        # --- Destination Groups Notebook / Container ---
        dest_container = tk.Frame(main_frame, bg=self.bg_color)
        dest_container.pack(fill=tk.BOTH, expand=True)

        # Group 1: Clinical & Nursing
        self._create_category_card(
            dest_container,
            title="💊 Clinical & Service Stations",
            destinations=[
                ("medicine_station", "💊 Medicine Station", "#0284c7"),
                ("nursing_station", "🩺 Nursing Station", "#0284c7"),
            ],
            row=0,
            col=0,
        )

        # Group 2: North Ward Patient Rooms
        self._create_category_card(
            dest_container,
            title="🛏️ North Ward (Patient & Exam Rooms)",
            destinations=[
                ("patient_room_101", "🛏️ Patient Room 101", "#2563eb"),
                ("patient_room_102", "🛏️ Patient Room 102", "#2563eb"),
                ("exam_room_103", "🔬 Exam Room 103", "#2563eb"),
                ("exam_room_104", "🔬 Exam Room 104", "#2563eb"),
            ],
            row=0,
            col=1,
        )

        # Group 3: South Ward Critical Care
        self._create_category_card(
            dest_container,
            title="🚨 Intensive Care Unit (ICU)",
            destinations=[
                ("icu_bay_a", "🚨 ICU Bay A", "#7c3aed"),
                ("icu_bay_b", "🚨 ICU Bay B", "#7c3aed"),
            ],
            row=1,
            col=0,
        )

        # Group 4: Specialized & Logistics
        self._create_category_card(
            dest_container,
            title="🏥 Specialized & East Wing",
            destinations=[
                ("surgical_suite", "🏥 Surgical Suite", "#059669"),
                ("clean_utility", "🧺 Clean Utility", "#059669"),
            ],
            row=1,
            col=1,
        )

        # Group 5: Base & Corridors
        self._create_category_card(
            dest_container,
            title="⚡ Corridors & Staging Base",
            destinations=[
                ("dispatch_base", "⚡ Dispatch & Docking Base", "#475569"),
                ("west_corridor", "↔️ West Corridor", "#475569"),
                ("central_crossroads", "➕ Central Crossroads", "#475569"),
            ],
            row=2,
            col=0,
            colspan=2,
        )

        # Configure grid weight
        dest_container.columnconfigure(0, weight=1)
        dest_container.columnconfigure(1, weight=1)

        # --- Footer Control Bar ---
        footer_frame = tk.Frame(main_frame, bg=self.bg_color, pady=10)
        footer_frame.pack(fill=tk.X)

        self.cancel_btn = tk.Button(
            footer_frame,
            text="🛑 CANCEL ACTIVE GOAL",
            font=("Helvetica", 11, "bold"),
            bg=self.accent_red,
            fg="#ffffff",
            activebackground="#991b1b",
            activeforeground="#ffffff",
            relief=tk.RAISED,
            padx=16,
            pady=8,
            state=tk.DISABLED,
            command=self._cancel_goal_clicked,
        )
        self.cancel_btn.pack(side=tk.LEFT)

        exit_btn = tk.Button(
            footer_frame,
            text="Close Interface",
            font=("Helvetica", 10),
            bg="#e2e8f0",
            fg=self.text_dark,
            padx=14,
            pady=8,
            command=self._on_close,
        )
        exit_btn.pack(side=tk.RIGHT)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_category_card(self, parent, title, destinations, row, col, colspan=1):
        """Helper to create a visually distinct category box with destination buttons."""
        card = tk.LabelFrame(
            parent,
            text=f" {title} ",
            font=("Helvetica", 11, "bold"),
            bg=self.card_bg,
            fg=self.text_dark,
            relief=tk.GROOVE,
            bd=1,
            padx=8,
            pady=8,
        )
        card.grid(row=row, column=col, columnspan=colspan, sticky="nsew", padx=4, pady=4)

        btn_grid = tk.Frame(card, bg=self.card_bg)
        btn_grid.pack(fill=tk.BOTH, expand=True)

        for i, (name, label, color) in enumerate(destinations):
            if not self.manager.has_waypoint(name):
                continue
            wp = self.manager.get_waypoint(name)
            btn = tk.Button(
                btn_grid,
                text=label,
                font=("Helvetica", 10, "bold"),
                bg=color,
                fg="#ffffff",
                activebackground="#1e293b",
                activeforeground="#ffffff",
                relief=tk.RAISED,
                padx=10,
                pady=6,
                cursor="hand2",
                command=lambda dest_name=name: self._dispatch_to(dest_name),
            )
            # Layout in 2 columns
            r = i // 2
            c = i % 2
            btn.grid(row=r, column=c, sticky="ew", padx=4, pady=4)
            btn_grid.columnconfigure(c, weight=1)
            self.destination_buttons[name] = btn

    def _check_nav2_connection(self):
        """Poll Nav2 action server readiness periodically."""
        if not rclpy.ok():
            return
        ready = self.ros_node.is_action_server_ready()
        if ready:
            if not self.is_navigating:
                self._update_status(
                    "Ready — Select a Destination Below",
                    "Nav2 action server '/navigate_to_pose' is active and ready.",
                    bg="#dcfce7",
                    fg=self.accent_green,
                )
        else:
            if not self.is_navigating:
                self._update_status(
                    "Connecting to Nav2 Action Server...",
                    "Waiting for Nav2 navigation stack (ensure navigation.launch.py is running).",
                    bg="#fef3c7",
                    fg="#b45309",
                )
        # Check again in 2 seconds
        try:
            self.root.after(2000, self._check_nav2_connection)
        except Exception:
            pass

    def _update_status(self, title: str, details: str, bg: str, fg: str):
        """Thread-safe UI status update."""
        self.status_frame.configure(bg=bg)
        self.status_title.configure(text=f"STATUS: {title}", bg=bg, fg=fg)
        self.status_details.configure(text=details, bg=bg)

    def _dispatch_to(self, waypoint_name: str):
        """Dispatch AHSER to the selected waypoint in a background thread."""
        if self.is_navigating:
            messagebox.showwarning(
                "Navigation in Progress",
                f"AHSER is currently navigating to '{self.current_goal_name}'.\nPlease cancel or wait for completion.",
            )
            return

        if not self.ros_node.is_action_server_ready():
            messagebox.showerror(
                "Nav2 Not Connected",
                "Nav2 action server '/navigate_to_pose' is not ready yet.\nPlease ensure navigation.launch.py is running.",
            )
            return

        wp = self.manager.get_waypoint(waypoint_name)
        self.is_navigating = True
        self.current_goal_name = waypoint_name
        self.cancel_btn.configure(state=tk.NORMAL)

        # Highlight active button
        for name, btn in self.destination_buttons.items():
            if name == waypoint_name:
                btn.configure(relief=tk.SUNKEN)
            else:
                btn.configure(state=tk.DISABLED)

        self._update_status(
            f"Navigating to '{wp.name}'...",
            f"Coordinates: X={wp.x:.2f} m, Y={wp.y:.2f} m | {wp.description}",
            bg="#dbeafe",
            fg=self.accent_blue,
        )

        # Run action dispatch in separate thread so UI never freezes
        threading.Thread(
            target=self._execute_navigation,
            args=(wp,),
            daemon=True,
        ).start()

    def _execute_navigation(self, wp: Waypoint):
        """Execute Nav2 NavigateToPose action."""
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = wp.to_pose_stamped(self.ros_node.get_clock().now().to_msg())

        send_future = self.ros_node._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self._on_navigation_feedback,
        )

        while not send_future.done():
            time.sleep(0.05)

        goal_handle = send_future.result()
        if not goal_handle.accepted:
            self.root.after(
                0,
                lambda: self._on_navigation_finished(
                    False, f"Goal rejected by Nav2 for '{wp.name}'."
                ),
            )
            return

        self.ros_node._current_goal_handle = goal_handle
        result_future = goal_handle.get_result_async()

        while not result_future.done():
            time.sleep(0.05)

        result = result_future.result()
        status = result.status

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.root.after(
                0,
                lambda: self._on_navigation_finished(
                    True, f"Successfully arrived at '{wp.name}' ({wp.description})!"
                ),
            )
        elif status == GoalStatus.STATUS_CANCELED:
            self.root.after(
                0,
                lambda: self._on_navigation_finished(
                    False, f"Navigation to '{wp.name}' was canceled."
                ),
            )
        else:
            self.root.after(
                0,
                lambda: self._on_navigation_finished(
                    False, f"Navigation to '{wp.name}' aborted (status {status})."
                ),
            )

    def _on_navigation_feedback(self, feedback_msg):
        """Update live distance remaining on GUI."""
        fb = feedback_msg.feedback
        dist = fb.distance_remaining
        elapsed = fb.navigation_time.sec + fb.navigation_time.nanosec * 1e-9
        self.root.after(
            0,
            lambda: self.status_details.configure(
                text=f"Distance remaining: {dist:.2f} m | Elapsed time: {elapsed:.1f} s | Target: {self.current_goal_name}"
            ),
        )

    def _on_navigation_finished(self, success: bool, message: str):
        """Reset UI state on navigation completion."""
        self.is_navigating = False
        self.cancel_btn.configure(state=tk.DISABLED)

        # Reset buttons
        for name, btn in self.destination_buttons.items():
            btn.configure(state=tk.NORMAL, relief=tk.RAISED)

        if success:
            self._update_status(
                "Arrived at Destination! 🎉",
                message,
                bg="#dcfce7",
                fg=self.accent_green,
            )
        else:
            self._update_status(
                "Navigation Stopped",
                message,
                bg="#fee2e2",
                fg=self.accent_red,
            )

    def _cancel_goal_clicked(self):
        """Cancel goal when user clicks the cancel button."""
        if self.is_navigating:
            self.status_details.configure(text="Canceling active navigation goal...")
            self.ros_node.cancel_active_goal()

    def _on_close(self):
        """Handle window close event cleanly."""
        if self.is_navigating:
            self.ros_node.cancel_active_goal()
        self.root.destroy()
        if rclpy.ok():
            rclpy.shutdown()
        sys.exit(0)


def main(args=None):
    root = tk.Tk()
    config_path = None
    if len(sys.argv) > 1 and sys.argv[1].endswith(".yaml"):
        config_path = sys.argv[1]
    app = WaypointGUI(root, config_path)
    root.mainloop()


if __name__ == "__main__":
    main()
