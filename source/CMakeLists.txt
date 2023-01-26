cmake_minimum_required(VERSION 3.1.3)
set (CMAKE_CXX_STANDARD 11)
project(MADA LANGUAGES CXX)

set(Targets MADA_iwaki MADA_con readIwaki SetVth read_CtrlMem SetDAC MADA_VthScan MADA_DACScan MADA_DAQenable MADA_DACAna)


if (NOT WIN32)
	find_library(PTHREAD_LIBRARIES pthread)
endif()

if (LIBM2K_VERSION)			# in-source build
	set(PROJECT_VERSION ${LIBM2K_VERSION})
else()					# standalone build
	set(PROJECT_VERSION "1.0.0")
	find_package(libm2k REQUIRED)
endif()

# Setting ROOT
list(APPEND CMAKE_PREFIX_PATH $ENV{ROOTSYS})
find_package(ROOT CONFIG REQUIRED)
include(${ROOT_USE_FILE})


add_executable(MADA_DAQenable MADA_DAQenable.cpp MADA_ad.cpp)
add_executable(MADA_DACScan MADA_DACScan.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(MADA_VthScan MADA_VthScan.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(MADA_DACAna MADA_DACAna.cxx)
target_link_libraries(MADA_DACAna ROOT::Core ROOT::Gpad ROOT::Hist ROOT::Rint)

add_executable(MADA_con MADA_con.cpp MADA_ad.cpp)
add_executable(readIwaki readIwaki.cpp SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(MADA_iwaki MADA_iwaki.cpp SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(SetVth SetVth.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(SetDAC SetDAC.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(read_CtrlMem read_CtrlMem.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)

target_link_libraries(MADA_con PRIVATE libm2k::libm2k)
target_link_libraries(MADA_DAQenable PRIVATE libm2k::libm2k)

set(CMAKE_INSTALL_PREFIX ${PROJECT_SOURCE_DIR}/..)
install(TARGETS ${Targets} RUNTIME DESTINATION bin)


