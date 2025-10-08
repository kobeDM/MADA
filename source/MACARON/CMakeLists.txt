cmake_minimum_required(VERSION 3.1.3)
set (CMAKE_CXX_STANDARD 11)
project(MADA LANGUAGES CXX)

set(Targets MACARON_DAQCtrl MACARON_CntReset MACARON_TPMode MACARON_CheckStatus)

if (NOT WIN32)
	find_library(PTHREAD_LIBRARIES pthread)
endif()

add_executable(MACARON_DAQCtrl MACARON_DAQCtrl.cxx GPIOUtil.cxx)
target_link_libraries(MACARON_DAQCtrl gpiod)
add_executable(MACARON_CntReset MACARON_CntReset.cxx GPIOUtil.cxx)
target_link_libraries(MACARON_CntReset gpiod)
add_executable(MACARON_TPMode MACARON_TPMode.cxx GPIOUtil.cxx)
target_link_libraries(MACARON_TPMode gpiod)
add_executable(MACARON_CheckStatus MACARON_CheckStatus.cxx GPIOUtil.cxx)
target_link_libraries(MACARON_CheckStatus gpiod)

set(CMAKE_INSTALL_PREFIX ${PROJECT_SOURCE_DIR}/../..)
install(TARGETS ${Targets} RUNTIME DESTINATION bin)


