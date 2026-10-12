# AHSER — Autonomous Hospital Service Robot

Autonomous Hospital Service Robot platform developed on ROS 2 Lyrical (Ubuntu 26.04) and Modern Gazebo (Jetty).

## Packages

- `ahser_description`: URDF/Xacro robot description, visual/collision geometry, materials, and display launch.
- `ahser_gazebo`: Modern Gazebo physics simulation, world definitions (`hospital_world.sdf`, `test_world.sdf`), and simulation bridge.
- `ahser_control`: Differential-drive controller and teleoperation configuration.
- `ahser_navigation`: SLAM Toolbox 2D LiDAR mapping configuration, RViz visualization, and map storage.
- `ahser_bringup`: Integrated system launch architecture.
- `ahser`: Umbrella meta-package.

## Simulation Workflows

### 1. Hospital Simulation World (Default)
The default simulation environment is a realistic 36m x 24m hospital floor plan featuring a main arterial corridor, patient wards, central nurse station, pharmacy, and an inpatient loop. AHSER spawns inside the **Robot Dispatch & Control Room** at `(x=-15.0m, y=1.0m, z=0.05m)`:

```bash
cd ~/Desktop/ahser_ws
source /opt/ros/lyrical/setup.bash
source install/setup.bash
ros2 launch ahser_gazebo simulation.launch.py
```

*(Alternatively, use the dedicated launch: `ros2 launch ahser_gazebo hospital_world.launch.py`)*

### 2. Legacy Test Arena (Optional)
To run the original 12m x 12m test arena instead:

```bash
ros2 launch ahser_gazebo simulation.launch.py world_name:=test_world
# Or:
ros2 launch ahser_gazebo test_world.launch.py
```

## 2D SLAM Mapping Workflow

Follow this terminal sequence to build a map of the hospital world:

1. **Terminal 1 — Simulation:**
   ```bash
   ros2 launch ahser_gazebo simulation.launch.py
   ```
2. **Terminal 2 — SLAM Toolbox & RViz:**
   ```bash
   ros2 launch ahser_navigation mapping.launch.py
   ```
3. **Terminal 3 — Teleoperation:**
   ```bash
   ros2 run teleop_twist_keyboard teleop_twist_keyboard
   ```
4. **Terminal 4 — Save Hospital Map:**
   ```bash
   ros2 run nav2_map_server map_saver_cli -f ~/Desktop/ahser_ws/src/ahser_navigation/maps/hospital_map --ros-args -p use_sim_time:=true
   ```

## Map Audit

- `hospital_map.yaml` / `hospital_map.pgm`: Target for the new hospital world map.
- `hospital_test_world.yaml` / `hospital_test_world.pgm`: Retained legacy map from Milestone 5. Audit confirmed this file represents the 12m x 12m test arena (origin `[-6.011, -5.994, 0]`, `240x239` pixels at `0.05m` resolution), not the hospital simulation world.
