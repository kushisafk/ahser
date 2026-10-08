import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_ahser_gazebo = FindPackageShare('ahser_gazebo')
    pkg_ros_gz_sim = FindPackageShare('ros_gz_sim')

    default_world_path = PathJoinSubstitution([
        pkg_ahser_gazebo, 'worlds', 'test_world.sdf'
    ])

    default_bridge_config_path = PathJoinSubstitution([
        pkg_ahser_gazebo, 'config', 'gazebo.yaml'
    ])

    world_arg = DeclareLaunchArgument(
        name='world',
        default_value=default_world_path,
        description='Full path to SDF world file to load'
    )

    gz_args_value = [
        '-r ', LaunchConfiguration('world')
    ]

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py'])
        ),
        launch_arguments={'gz_args': gz_args_value}.items()
    )

    ros_gz_bridge_node = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        output='screen',
        parameters=[{
            'config_file': default_bridge_config_path,
            'use_sim_time': True
        }]
    )

    return LaunchDescription([
        world_arg,
        gz_sim,
        ros_gz_bridge_node
    ])
