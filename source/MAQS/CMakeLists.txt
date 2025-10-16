cmake_minimum_required(VERSION 3.1.3)
set (CMAKE_CXX_STANDARD 11)
project(MADA LANGUAGES CXX)

set(Targets MADA_iwaki SetVth read_CtrlMem SetDAC MADA_VthScan MADA_VthAna MADA_DACScan MADA_DACAna)

if (NOT WIN32)
	find_library(PTHREAD_LIBRARIES pthread)
endif()

# Setting ROOT
list(APPEND CMAKE_PREFIX_PATH $ENV{ROOTSYS})
find_package(ROOT CONFIG REQUIRED)
include(${ROOT_USE_FILE})

add_executable(MADA_DACScan MADA_DACScan.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(MADA_VthScan MADA_VthScan.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(MADA_DACAna MADA_DACAna.cxx)
add_executable(MADA_VthAna MADA_VthAna.cxx)
target_link_libraries(MADA_DACAna ROOT::Core ROOT::Gpad ROOT::Hist ROOT::Rint)
target_link_libraries(MADA_VthAna ROOT::Core ROOT::Gpad ROOT::Hist ROOT::Rint)

add_executable(MADA_iwaki MADA_iwaki.cpp SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(SetVth SetVth.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(SetDAC SetDAC.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(read_CtrlMem read_CtrlMem.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)

set(CMAKE_INSTALL_PREFIX ${PROJECT_SOURCE_DIR}/../../)
install(TARGETS ${Targets} RUNTIME DESTINATION bin)


