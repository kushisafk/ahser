cmake_minimum_required(VERSION 3.20)
project(ahser_gazebo)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch models worlds
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
