"""AHSER Navigation Launch File (Skeleton)."""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_ahser_navigation = FindPackageShare('ahser_navigation')

    default_nav2_params = PathJoinSubstitution([
        pkg_ahser_navigation, 'config', 'nav2_params.yaml'
    ])

    use_sim_time_arg = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )

    params_file_arg = DeclareLaunchArgument(
        name='params_file',
        default_value=default_nav2_params,
        description='Full path to the ROS 2 Nav2 parameters file'
    )

    autostart_arg = DeclareLaunchArgument(
        name='autostart',
        default_value='true',
        description='Automatically startup the nav2 stack'
    )

    log_info = LogInfo(
        msg='AHSER navigation launch skeleton loaded. Nav2 stack integration will be configured in navigation phase.'
    )

    return LaunchDescription([
        use_sim_time_arg,
        params_file_arg,
        autostart_arg,
        log_info
    ])
