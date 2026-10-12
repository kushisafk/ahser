"""AHSER Nav2 Autonomous Navigation Launch File.

Launches Nav2 localization (map_server, amcl), navigation servers
(controller, planner, recovery behaviors, bt_navigator), lifecycle manager,
and RViz2 visualization for autonomous indoor hospital navigation.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, SetParameter
from launch_ros.substitutions import FindPackageShare
from nav2_common.launch import RewrittenYaml


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

    # Declare launch arguments
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

    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM', '1'
    )

    # Substitute dynamic launch arguments into parameter file
    param_substitutions = {
        'use_sim_time': LaunchConfiguration('use_sim_time'),
        'yaml_filename': LaunchConfiguration('map'),
        'autostart': LaunchConfiguration('autostart'),
    }

    configured_params = RewrittenYaml(
        source_file=LaunchConfiguration('params_file'),
        root_key='',
        param_rewrites=param_substitutions,
        convert_types=True
    )

    lifecycle_nodes = [
        'map_server',
        'amcl',
        'controller_server',
        'planner_server',
        'behavior_server',
        'bt_navigator'
    ]

    # Map Server node
    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[
            configured_params,
            {'yaml_filename': LaunchConfiguration('map')}
        ],
    )

    # AMCL Localization node
    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[configured_params],
    )

    # Controller Server (Local Planner)
    controller_server_node = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[configured_params],
        remappings=[('cmd_vel', '/cmd_vel')],
    )

    # Planner Server (Global Planner)
    planner_server_node = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[configured_params],
    )

    # Behavior Server (Recovery Behaviors)
    behavior_server_node = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[configured_params],
        remappings=[('cmd_vel', '/cmd_vel')],
    )

    # BT Navigator (Behavior Tree Navigation)
    bt_navigator_node = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[configured_params],
    )

    # Lifecycle Manager for Nav2 stack
    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'autostart': LaunchConfiguration('autostart'),
            'node_names': lifecycle_nodes,
        }],
    )

    # RViz2 visualization
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
        map_server_node,
        amcl_node,
        controller_server_node,
        planner_server_node,
        behavior_server_node,
        bt_navigator_node,
        lifecycle_manager_node,
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
        nav2_group,
    ])
