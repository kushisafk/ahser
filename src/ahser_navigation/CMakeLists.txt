cmake_minimum_required(VERSION 3.20)
project(ahser_navigation)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch rviz maps
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
