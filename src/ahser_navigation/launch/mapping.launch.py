"""AHSER 2D SLAM Mapping Launch File using SLAM Toolbox.

Supports both fresh mapping from scratch and continuing mapping from an
existing saved pose-graph (hospital_map.posegraph) so new rooms and corridors
can be seamlessly appended to the existing map.
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.conditions import IfCondition
from launch.events import matches_action
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import LifecycleNode, Node
from launch_ros.descriptions import ParameterFile
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from launch_ros.substitutions import FindPackageShare
from lifecycle_msgs.msg import Transition


def launch_slam_toolbox(context):
    use_sim_time = LaunchConfiguration('use_sim_time').perform(context).lower() == 'true'
    continue_mapping = LaunchConfiguration('continue_mapping').perform(context).lower() == 'true'
    map_file_name = LaunchConfiguration('map_file_name').perform(context)
    slam_params_file = LaunchConfiguration('slam_params_file').perform(context)

    node_params = [
        ParameterFile(slam_params_file, allow_substs=True),
        {
            'use_sim_time': use_sim_time,
            'use_lifecycle_manager': False,
        }
    ]

    if continue_mapping:
        node_params.append({
            'map_file_name': map_file_name,
            'map_start_pose': [0.0, 0.0, 0.0],
        })

    slam_node = LifecycleNode(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=node_params,
        namespace=''
    )

    configure_event = EmitEvent(
        event=ChangeState(
            lifecycle_node_matcher=matches_action(slam_node),
            transition_id=Transition.TRANSITION_CONFIGURE
        )
    )

    activate_event = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=slam_node,
            start_state='configuring',
            goal_state='inactive',
            entities=[
                LogInfo(msg='[LifecycleLaunch] Slamtoolbox node is activating.'),
                EmitEvent(event=ChangeState(
                    lifecycle_node_matcher=matches_action(slam_node),
                    transition_id=Transition.TRANSITION_ACTIVATE
                ))
            ]
        )
    )

    return [slam_node, configure_event, activate_event]


def generate_launch_description():
    pkg_ahser_navigation = FindPackageShare('ahser_navigation')

    default_slam_params = PathJoinSubstitution([
        pkg_ahser_navigation, 'config', 'slam_toolbox.yaml'
    ])
    default_rviz_config = PathJoinSubstitution([
        pkg_ahser_navigation, 'rviz', 'mapping.rviz'
    ])
    default_map_file = PathJoinSubstitution([
        pkg_ahser_navigation, 'maps', 'hospital_map'
    ])

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

    continue_mapping_arg = DeclareLaunchArgument(
        name='continue_mapping',
        default_value='false',
        description='Continue mapping from existing saved pose-graph if true'
    )

    map_file_name_arg = DeclareLaunchArgument(
        name='map_file_name',
        default_value=default_map_file,
        description='Full path to pose-graph file (without .posegraph extension) for continuing SLAM'
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
        continue_mapping_arg,
        map_file_name_arg,
        use_rviz_arg,
        rviz_config_arg,
        OpaqueFunction(function=launch_slam_toolbox),
        rviz_node,
    ])
