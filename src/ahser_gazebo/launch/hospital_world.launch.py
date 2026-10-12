"""AHSER Dedicated Hospital World Simulation Launch File."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_ahser_gazebo = FindPackageShare('ahser_gazebo')

    headless_arg = DeclareLaunchArgument(
        name='headless',
        default_value='false',
        description='Run Gazebo headless (no GUI) if true'
    )

    x_arg = DeclareLaunchArgument(
        name='x',
        default_value='-15.0',
        description='Initial X position in world coordinates (meters) - starts in Robot Dispatch Base (-15.0m)'
    )

    y_arg = DeclareLaunchArgument(
        name='y',
        default_value='1.0',
        description='Initial Y position in world coordinates (meters) - starts in Robot Dispatch Base (1.0m)'
    )

    z_arg = DeclareLaunchArgument(
        name='z',
        default_value='0.05',
        description='Initial Z spawn height (meters)'
    )

    yaw_arg = DeclareLaunchArgument(
        name='yaw',
        default_value='0.0',
        description='Initial Yaw orientation in world coordinates (radians)'
    )

    simulation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_ahser_gazebo, 'launch', 'simulation.launch.py'])
        ),
        launch_arguments={
            'world_name': 'hospital_world',
            'headless': LaunchConfiguration('headless'),
            'x': LaunchConfiguration('x'),
            'y': LaunchConfiguration('y'),
            'z': LaunchConfiguration('z'),
            'yaw': LaunchConfiguration('yaw'),
        }.items()
    )

    return LaunchDescription([
        headless_arg,
        x_arg,
        y_arg,
        z_arg,
        yaw_arg,
        simulation_launch,
    ])
