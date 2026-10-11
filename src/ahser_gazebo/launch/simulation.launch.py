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

    # Path to simulation assets
    default_world_path = PathJoinSubstitution([
        pkg_ahser_gazebo, 'worlds', 'test_world.sdf'
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

    x_arg = DeclareLaunchArgument(
        name='x',
        default_value='0.0',
        description='Initial X position in world coordinates (meters)'
    )

    y_arg = DeclareLaunchArgument(
        name='y',
        default_value='0.0',
        description='Initial Y position in world coordinates (meters)'
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
            '-world', 'test_world',
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
