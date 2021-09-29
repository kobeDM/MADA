cmake_minimum_required(VERSION 3.1.3)
set (CMAKE_CXX_STANDARD 11)
project(MADA LANGUAGES CXX)

set(Targets MADA MADA_con readIwaki SetVth read_CtrlMem SetDAC MADA_VthScan MADA_DACScan MADA_DAQenable)


if (NOT WIN32)
	find_library(PTHREAD_LIBRARIES pthread)
endif()

if (LIBM2K_VERSION)			# in-source build
	set(PROJECT_VERSION ${LIBM2K_VERSION})
else()					# standalone build
	set(PROJECT_VERSION "1.0.0")
	find_package(libm2k REQUIRED)
      endif()

#if (LIBM2K_VERSION)			# in-source build#
#	set(PROJECT_VERSION ${LIBM2K_VERSION})
#else()					# standalone build
#	set(PROJECT_VERSION "1.0.0")
#	find_package(SiTCP REQUIRED)
	find_package(Threads REQUIRED)
 #     endif()

list(APPEND CMAKE_PREFIX_PATH $ENV{ROOTSYS})
find_package(ROOT REQUIRED COMPONENTS RIO Net)
include(${ROOT_USE_FILE})
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)
file(GLOB headers ${PROJECT_SOURCE_DIR}/include/*.hh)
file(GLOB sources ${PROJECT_SOURCE_DIR}/src/*.cc)

     
#add_executable(MADA MADA_ad.cpp MADA_iwaki.cpp SiTCP.cxx TCPclient.cxx RBCP.cxx)
#add_executable(MADA_DACAna MADA_DACAna.cxx )
add_executable(MADA_DAQenable MADA_DAQenable.cpp MADA_ad.cpp MADA_iwaki.cpp SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(MADA_DACScan MADA_DACScan.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(MADA_VthScan MADA_VthScan.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(MADA_con MADA_con.cpp MADA_ad.cpp)
#add_executable(MADA_VthAna MADA_VthAna.cxx)
   #MADA_iwaki.cpp SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(readIwaki readIwaki.cpp SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(MADA MADA.cpp MADA_ad.cpp MADA_iwaki.cpp SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(SetVth SetVth.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(SetDAC SetDAC.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
add_executable(read_CtrlMem read_CtrlMem.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
#add_executable(GigaDAQ GigaDAQ.cxx SiTCP.cxx TCPclient.cxx RBCP.cxx)
#add_executable(ad_dout "ad_dout.cpp")
#add_executable(ad_out "ad_out.cpp")
#add_executable(daq_test "daq_test.cpp")
#add_executable(daq_sahigash "daq_sahigash.cpp")
#target_link_libraries(MADA_DAQcheck ${ROOT_LIBRARIES})
#foreach(path IN LISTS Targets)
#  get_filename_component(target ${path} NAME_WE)
#  add_executable(${target} ${path}
#                 ${sources} ${headers})
#  target_link_libraries(${target} ${ROOT_LIBRARIES})
#endforeach()


target_link_libraries(MADA_con PRIVATE libm2k::libm2k)
target_link_libraries(MADA_DAQenable PRIVATE libm2k::libm2k)
target_link_libraries(MADA PRIVATE libm2k::libm2k)
target_link_libraries(MADA PRIVATE Threads::Threads)
#target_link_libraries(MADA PRIVATE SiTCP::SiTCP)
#target_link_libraries(ad_aout PRIVATE libm2k::libm2k)
#target_link_libraries(daq_test PRIVATE libm2k::libm2k)
#target_link_libraries(daq_sahigash PRIVATE libm2k::libm2k)

set(CMAKE_INSTALL_PREFIX ${PROJECT_SOURCE_DIR}/..)
#install(TARGETS MADA MADA_con readIwaki SetVth read_CtrlMem SetDAC RUNTIME DESTINATION bin)
install(TARGETS ${Targets} RUNTIME DESTINATION bin)
#install(TARGETS MADA_iwaki RUNTIME DESTINATION bin)


