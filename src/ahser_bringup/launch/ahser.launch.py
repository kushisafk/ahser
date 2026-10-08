"""AHSER Master Bringup Launch File."""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_ahser_bringup = FindPackageShare('ahser_bringup')
    pkg_ahser_description = FindPackageShare('ahser_description')
    pkg_ahser_gazebo = FindPackageShare('ahser_gazebo')

    # Launch configuration variables
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('rviz')

    # Declare launch arguments
    use_sim_time_arg = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )

    use_rviz_arg = DeclareLaunchArgument(
        name='rviz',
        default_value='false',
        description='Open RViz2 if true'
    )

    # Robot Description
    xacro_file = PathJoinSubstitution([
        pkg_ahser_description, 'urdf', 'ahser.urdf.xacro'
    ])

    robot_description_content = Command([
        'xacro ', xacro_file
    ])

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_content,
            'use_sim_time': use_sim_time
        }]
    )

    # Gazebo simulation launch
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_ahser_gazebo, 'launch', 'simulation.launch.py'])
        )
    )

    # Optional RViz launch
    rviz_config_file = PathJoinSubstitution([
        pkg_ahser_description, 'rviz', 'ahser.rviz'
    ])

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(use_rviz)
    )

    return LaunchDescription([
        use_sim_time_arg,
        use_rviz_arg,
        robot_state_publisher_node,
        gazebo_launch,
        rviz_node
    ])
