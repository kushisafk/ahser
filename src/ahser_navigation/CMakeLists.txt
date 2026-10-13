cmake_minimum_required(VERSION 3.20)
project(ahser_navigation)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

install(
  DIRECTORY config launch rviz maps
  DESTINATION share/${PROJECT_NAME}
)

ament_python_install_package(${PROJECT_NAME})

install(
  PROGRAMS scripts/waypoint_navigator.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME waypoint_navigator
)

install(
  PROGRAMS scripts/waypoint_navigator.py
  DESTINATION lib/${PROJECT_NAME}
)

install(
  PROGRAMS scripts/waypoint_gui.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME waypoint_gui
)

install(
  PROGRAMS scripts/waypoint_gui.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
