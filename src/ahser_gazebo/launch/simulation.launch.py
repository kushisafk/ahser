"""AHSER Gazebo Jetty Physics Simulation Launch File."""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_ahser_gazebo = FindPackageShare('ahser_gazebo')
    pkg_ahser_description = FindPackageShare('ahser_description')
    pkg_ros_gz_sim = FindPackageShare('ros_gz_sim')

    world_name_arg = DeclareLaunchArgument(
        name='world_name',
        default_value='hospital_world',
        description='Name of the Gazebo world defined inside the SDF (e.g. hospital_world or test_world)'
    )

    # Path to simulation assets (defaults dynamically to world_name.sdf)
    default_world_path = PathJoinSubstitution([
        pkg_ahser_gazebo, 'worlds',
        PythonExpression(["'", LaunchConfiguration('world_name'), ".sdf'"])
    ])
    default_bridge_config_path = PathJoinSubstitution([
        pkg_ahser_gazebo, 'config', 'gazebo.yaml'
    ])
    default_xacro_path = PathJoinSubstitution([
        pkg_ahser_description, 'urdf', 'ahser.urdf.xacro'
    ])

    # Declare launch arguments
    world_arg = DeclareLaunchArgument(
        name='world',
        default_value=default_world_path,
        description='Full path to SDF world file to load'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )

    robot_name_arg = DeclareLaunchArgument(
        name='robot_name',
        default_value='ahser',
        description='Entity name for the spawned robot model in Gazebo'
    )

    default_x = PythonExpression([
        "'-15.0' if '", LaunchConfiguration('world_name'), "' == 'hospital_world' else '0.0'"
    ])
    default_y = PythonExpression([
        "'1.0' if '", LaunchConfiguration('world_name'), "' == 'hospital_world' else '0.0'"
    ])

    x_arg = DeclareLaunchArgument(
        name='x',
        default_value=default_x,
        description='Initial X position in world coordinates (meters) - starts in Control Room (-15.0m) for hospital world'
    )

    y_arg = DeclareLaunchArgument(
        name='y',
        default_value=default_y,
        description='Initial Y position in world coordinates (meters) - starts in Control Room (1.0m) for hospital world'
    )

    z_arg = DeclareLaunchArgument(
        name='z',
        default_value='0.05',
        description='Initial Z spawn height (meters) - starts above ground without penetrating'
    )

    yaw_arg = DeclareLaunchArgument(
        name='yaw',
        default_value='0.0',
        description='Initial Yaw orientation in world coordinates (radians)'
    )

    headless_arg = DeclareLaunchArgument(
        name='headless',
        default_value='false',
        description='Run Gazebo headless (no GUI) if true'
    )

    # Process existing AHSER Xacro description from ahser_description
    robot_description_content = ParameterValue(
        Command(['xacro ', default_xacro_path]),
        value_type=str
    )

    # Robot State Publisher publishes the robot description and broadcasts TFs
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_content,
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }]
    )

    # Modern Gazebo Sim (Jetty) process execution
    gz_args = PythonExpression([
        "('-r -s ' if '", LaunchConfiguration('headless'), "' == 'true' else '-r ') + '",
        LaunchConfiguration('world'), "'"
    ])

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py'])
        ),
        launch_arguments={
            'gz_args': gz_args,
            'on_exit_shutdown': 'true'
        }.items()
    )

    # Spawn AHSER entity in Gazebo using ros_gz_sim create node
    spawn_robot_node = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_ahser',
        output='screen',
        arguments=[
            '-world', LaunchConfiguration('world_name'),
            '-name', LaunchConfiguration('robot_name'),
            '-topic', 'robot_description',
            '-x', LaunchConfiguration('x'),
            '-y', LaunchConfiguration('y'),
            '-z', LaunchConfiguration('z'),
            '-Y', LaunchConfiguration('yaw')
        ]
    )

    # ROS-Gazebo bridge for simulation clock synchronization
    ros_gz_bridge_node = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        output='screen',
        parameters=[{
            'config_file': default_bridge_config_path,
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }]
    )

    return LaunchDescription([
        world_name_arg,
        world_arg,
        use_sim_time_arg,
        robot_name_arg,
        x_arg,
        y_arg,
        z_arg,
        yaw_arg,
        headless_arg,
        robot_state_publisher_node,
        gz_sim,
        spawn_robot_node,
        ros_gz_bridge_node,
    ])
