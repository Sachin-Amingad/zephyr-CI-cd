cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED)
project(hello_world)

add_executable(app src/main.c)
target_sources(app PRIVATE src/main.c)
target_link_libraries(app PRIVATE zephyr_interface)