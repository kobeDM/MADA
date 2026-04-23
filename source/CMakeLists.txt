cmake_minimum_required(VERSION 3.1.3)

project(MADA LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(Targets
    MADA_iwaki
    MADA_con
    readIwaki
    SetVth
    read_CtrlMem
    SetDAC
    MADA_VthScan
    MADA_DACScan
    MADA_DAQenable
    SetADCBias
    SetAP
    SetLatchUpDetect
    DAC_Analysis
    DAC_Survey
)

find_package(Threads REQUIRED)
find_package(libm2k REQUIRED)

list(APPEND CMAKE_PREFIX_PATH $ENV{ROOTSYS})
find_package(ROOT REQUIRED COMPONENTS RIO Net)
include(${ROOT_USE_FILE})

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(MADA_DAQenable MADA_DAQenable.cc MADA_ad.cc)
add_executable(MADA_DACScan MADA_DACScan.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(MADA_VthScan MADA_VthScan.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(MADA_con MADA_con.cc MADA_ad.cc)
add_executable(readIwaki readIwaki.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(MADA_iwaki MADA_iwaki.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(SetVth SetVth.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(SetDAC SetDAC.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(read_CtrlMem read_CtrlMem.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(SetADCBias SetADCBias.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(SetAP SetAP.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(SetLatchUpDetect SetLatchUpDetect.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(DAC_Analysis DAC_Analysis.cc )
add_executable(DAC_Survey DAC_Survey.cc RBCP.cc SiTCP.cc )

target_link_libraries(MADA_con PRIVATE libm2k::libm2k ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(MADA_DAQenable PRIVATE libm2k::libm2k ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(MADA_DACScan PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(MADA_VthScan PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(readIwaki PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(MADA_iwaki PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(SetVth PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(SetDAC PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(read_CtrlMem PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(SetADCBias PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(SetAP PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(SetLatchUpDetect PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(DAC_Analysis PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(DAC_Survey PRIVATE ${ROOT_LIBRARIES} Threads::Threads)

set(CMAKE_INSTALL_PREFIX ${PROJECT_SOURCE_DIR}/..)

install(TARGETS ${Targets} RUNTIME DESTINATION bin)

add_custom_target(distclean
    COMMAND ${CMAKE_COMMAND} --build . --target clean
    COMMAND ${CMAKE_COMMAND} -E rm -rf ${CMAKE_INSTALL_PREFIX}/bin
)