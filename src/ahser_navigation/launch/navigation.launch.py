"""AHSER Nav2 Autonomous Navigation Launch File.

Supports two navigation modes:
1. Standard Saved-Map Navigation (slam:=false, default):
   Uses map_server + AMCL localization against hospital_map.yaml.
2. Dynamic Expanding SLAM Navigation (slam:=true):
   Replaces AMCL with SLAM Toolbox so AHSER can navigate autonomously with
   2D Goal Pose into unmapped areas and dynamically expand the hospital map.
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    GroupAction,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.events import matches_action
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import LifecycleNode, Node, SetParameter
from launch_ros.descriptions import ParameterFile
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from launch_ros.substitutions import FindPackageShare
from lifecycle_msgs.msg import Transition
from nav2_common.launch import RewrittenYaml


def launch_localization_and_lifecycle(context):
    slam_enabled = LaunchConfiguration('slam').perform(context).lower() == 'true'
    use_sim_time = LaunchConfiguration('use_sim_time').perform(context).lower() == 'true'
    autostart = LaunchConfiguration('autostart').perform(context).lower() == 'true'
    continue_mapping = LaunchConfiguration('continue_mapping').perform(context).lower() == 'true'
    map_file_name = LaunchConfiguration('map_file_name').perform(context)
    slam_params_file = LaunchConfiguration('slam_params_file').perform(context)
    map_path = LaunchConfiguration('map').perform(context)
    params_file = LaunchConfiguration('params_file').perform(context)

    # Rewritten params for Nav2 nodes
    param_substitutions = {
        'use_sim_time': str(use_sim_time).lower(),
        'yaml_filename': map_path,
        'autostart': str(autostart).lower(),
    }
    configured_params = RewrittenYaml(
        source_file=params_file,
        root_key='',
        param_rewrites=param_substitutions,
        convert_types=True
    )

    actions = []

    if not slam_enabled:
        # Standard Mode: Map Server + AMCL
        map_server_node = Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            output='screen',
            parameters=[configured_params, {'yaml_filename': map_path}],
        )
        amcl_node = Node(
            package='nav2_amcl',
            executable='amcl',
            name='amcl',
            output='screen',
            parameters=[configured_params],
        )
        lifecycle_nodes = [
            'map_server',
            'amcl',
            'controller_server',
            'planner_server',
            'behavior_server',
            'bt_navigator'
        ]
        actions.extend([map_server_node, amcl_node])
    else:
        # SLAM Navigation Mode: SLAM Toolbox provides dynamic /map and map->odom TF
        slam_params = [
            ParameterFile(slam_params_file, allow_substs=True),
            {
                'use_sim_time': use_sim_time,
                'use_lifecycle_manager': False,
            }
        ]
        if continue_mapping:
            slam_params.append({
                'map_file_name': map_file_name,
                'map_start_pose': [0.0, 0.0, 0.0],
            })

        slam_node = LifecycleNode(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=slam_params,
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
        lifecycle_nodes = [
            'controller_server',
            'planner_server',
            'behavior_server',
            'bt_navigator'
        ]
        actions.extend([slam_node, configure_event, activate_event])

    # Common Nav2 Navigation Nodes
    controller_server_node = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[configured_params],
        remappings=[('cmd_vel', '/cmd_vel')],
    )

    planner_server_node = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[configured_params],
    )

    behavior_server_node = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[configured_params],
        remappings=[('cmd_vel', '/cmd_vel')],
    )

    bt_navigator_node = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[configured_params],
    )

    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': autostart,
            'node_names': lifecycle_nodes,
        }],
    )

    actions.extend([
        controller_server_node,
        planner_server_node,
        behavior_server_node,
        bt_navigator_node,
        lifecycle_manager_node,
    ])

    return actions


def generate_launch_description():
    pkg_ahser_navigation = FindPackageShare('ahser_navigation')

    default_map_path = PathJoinSubstitution([
        pkg_ahser_navigation, 'maps', 'hospital_map.yaml'
    ])
    default_params_file = PathJoinSubstitution([
        pkg_ahser_navigation, 'config', 'nav2_params.yaml'
    ])
    default_rviz_config = PathJoinSubstitution([
        pkg_ahser_navigation, 'rviz', 'navigation.rviz'
    ])
    default_slam_params = PathJoinSubstitution([
        pkg_ahser_navigation, 'config', 'slam_toolbox.yaml'
    ])
    default_map_posegraph = PathJoinSubstitution([
        pkg_ahser_navigation, 'maps', 'hospital_map'
    ])

    use_sim_time_arg = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )
    map_arg = DeclareLaunchArgument(
        name='map',
        default_value=default_map_path,
        description='Full path to map YAML file to load'
    )
    params_file_arg = DeclareLaunchArgument(
        name='params_file',
        default_value=default_params_file,
        description='Full path to the ROS 2 Nav2 parameters file'
    )
    autostart_arg = DeclareLaunchArgument(
        name='autostart',
        default_value='true',
        description='Automatically startup the nav2 stack'
    )
    use_rviz_arg = DeclareLaunchArgument(
        name='use_rviz',
        default_value='true',
        description='Launch RViz2 for navigation visualization if true'
    )
    rviz_config_arg = DeclareLaunchArgument(
        name='rviz_config',
        default_value=default_rviz_config,
        description='Full path to the RViz configuration file'
    )
    slam_arg = DeclareLaunchArgument(
        name='slam',
        default_value='false',
        description='Run SLAM Toolbox instead of AMCL to dynamically map new areas while navigating'
    )
    continue_mapping_arg = DeclareLaunchArgument(
        name='continue_mapping',
        default_value='true',
        description='When slam:=true, pre-load existing pose-graph to keep known rooms'
    )
    map_file_name_arg = DeclareLaunchArgument(
        name='map_file_name',
        default_value=default_map_posegraph,
        description='Full path to pose-graph file without extension for continuing SLAM'
    )
    slam_params_file_arg = DeclareLaunchArgument(
        name='slam_params_file',
        default_value=default_slam_params,
        description='Path to SLAM Toolbox configuration file when slam:=true'
    )

    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM', '1'
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2_navigation',
        arguments=['-d', LaunchConfiguration('rviz_config')],
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}],
        condition=IfCondition(LaunchConfiguration('use_rviz')),
    )

    nav2_group = GroupAction([
        SetParameter('use_sim_time', LaunchConfiguration('use_sim_time')),
        OpaqueFunction(function=launch_localization_and_lifecycle),
        rviz_node,
    ])

    return LaunchDescription([
        stdout_linebuf_envvar,
        use_sim_time_arg,
        map_arg,
        params_file_arg,
        autostart_arg,
        use_rviz_arg,
        rviz_config_arg,
        slam_arg,
        continue_mapping_arg,
        map_file_name_arg,
        slam_params_file_arg,
        nav2_group,
    ])
