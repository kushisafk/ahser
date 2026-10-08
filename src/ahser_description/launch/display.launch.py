"""AHSER Robot Description Display Launch File."""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Resolve package paths dynamically using FindPackageShare
    pkg_ahser_description = FindPackageShare('ahser_description')

    default_xacro_path = PathJoinSubstitution([
        pkg_ahser_description, 'urdf', 'ahser.urdf.xacro'
    ])

    default_rviz_path = PathJoinSubstitution([
        pkg_ahser_description, 'rviz', 'ahser.rviz'
    ])

    # Declare launch arguments
    use_sim_time_arg = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true'
    )

    gui_arg = DeclareLaunchArgument(
        name='gui',
        default_value='true',
        description='Enable joint_state_publisher_gui slider interface'
    )

    rviz_config_arg = DeclareLaunchArgument(
        name='rviz_config',
        default_value=default_rviz_path,
        description='Full path to the RViz configuration file'
    )

    # Process Xacro into robot_description XML string wrapped as ParameterValue
    robot_description_content = ParameterValue(
        Command(['xacro ', default_xacro_path]),
        value_type=str
    )

    # Robot State Publisher broadcasts TF coordinates for all links
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

    # Standard Joint State Publisher (headless/scripted mode)
    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time')
        }],
        condition=UnlessCondition(LaunchConfiguration('gui'))
    )

    # Joint State Publisher with GUI sliders for continuous/revolute joints
    joint_state_publisher_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen',
        condition=IfCondition(LaunchConfiguration('gui'))
    )

    # RViz2 visualization node
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', LaunchConfiguration('rviz_config')],
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time')
        }]
    )

    return LaunchDescription([
        use_sim_time_arg,
        gui_arg,
        rviz_config_arg,
        robot_state_publisher_node,
        joint_state_publisher_node,
        joint_state_publisher_gui_node,
        rviz_node
    ])
