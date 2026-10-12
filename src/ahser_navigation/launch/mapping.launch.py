"""AHSER 2D SLAM Mapping Launch File using SLAM Toolbox."""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_ahser_navigation = FindPackageShare('ahser_navigation')
    pkg_slam_toolbox = FindPackageShare('slam_toolbox')

    default_slam_params = PathJoinSubstitution([
        pkg_ahser_navigation, 'config', 'slam_toolbox.yaml'
    ])
    default_rviz_config = PathJoinSubstitution([
        pkg_ahser_navigation, 'rviz', 'mapping.rviz'
    ])

    # Declare launch arguments
    use_sim_time_arg = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )

    slam_params_file_arg = DeclareLaunchArgument(
        name='slam_params_file',
        default_value=default_slam_params,
        description='Full path to the SLAM Toolbox parameters file'
    )

    use_rviz_arg = DeclareLaunchArgument(
        name='use_rviz',
        default_value='true',
        description='Launch RViz2 for SLAM mapping visualization if true'
    )

    rviz_config_arg = DeclareLaunchArgument(
        name='rviz_config',
        default_value=default_rviz_config,
        description='Full path to the RViz configuration file'
    )

    # Include SLAM Toolbox online async mapping node with lifecycle autostart
    slam_toolbox_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                pkg_slam_toolbox, 'launch', 'online_async_launch.py'
            ])
        ),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'slam_params_file': LaunchConfiguration('slam_params_file'),
        }.items()
    )

    # Launch RViz2 visualization for 2D mapping
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2_mapping',
        output='screen',
        arguments=['-d', LaunchConfiguration('rviz_config')],
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time')
        }],
        condition=IfCondition(LaunchConfiguration('use_rviz'))
    )

    return LaunchDescription([
        use_sim_time_arg,
        slam_params_file_arg,
        use_rviz_arg,
        rviz_config_arg,
        slam_toolbox_launch,
        rviz_node,
    ])
