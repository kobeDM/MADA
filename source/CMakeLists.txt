cmake_minimum_required(VERSION 3.1.3)

project(MADA LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(Targets
    MADA_iwaki
    SetVth
    read_CtrlMem
    SetDAC
    SetADCBias
    SetAP
    SetLatchUpDetect
    DAC_Analysis
    DAC_Survey
    ScanVth
    Vth_Analysis
    FindAdalm
    AdalmControl
    OutputTestPulse
    SetAllDAC
)

find_package(Threads REQUIRED)
find_package(libm2k REQUIRED)

list(APPEND CMAKE_PREFIX_PATH $ENV{ROOTSYS})
find_package(ROOT REQUIRED COMPONENTS RIO Net)
include(${ROOT_USE_FILE})

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(MADA_iwaki MADA_iwaki.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(SetVth SetVth.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(SetDAC SetDAC.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(read_CtrlMem read_CtrlMem.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(SetADCBias SetADCBias.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(SetAP SetAP.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(SetLatchUpDetect SetLatchUpDetect.cc SiTCP.cc TCPclient.cc RBCP.cc)
add_executable(DAC_Analysis DAC_Analysis.cc )
add_executable(DAC_Survey DAC_Survey.cc RBCP.cc SiTCP.cc )
add_executable(ScanVth ScanVth.cc SiTCP.cc RBCP.cc)
add_executable(Vth_Analysis Vth_Analysis.cc)
add_executable(FindAdalm FindAdalm.cc)
add_executable(AdalmControl AdalmControl.cc AdalmUtil.cc)
add_executable(OutputTestPulse OutputTestPulse.cc AdalmUtil.cc)
add_executable(SetAllDAC SetAllDAC.cc RBCP.cc)

target_link_libraries(AdalmControl PRIVATE libm2k::libm2k ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(OutputTestPulse PRIVATE libm2k::libm2k ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(MADA_iwaki PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(SetVth PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(SetDAC PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(read_CtrlMem PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(SetADCBias PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(SetAP PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(SetLatchUpDetect PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(DAC_Analysis PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(DAC_Survey PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(ScanVth PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(Vth_Analysis PRIVATE ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(FindAdalm PRIVATE libm2k::libm2k ${ROOT_LIBRARIES} Threads::Threads)
target_link_libraries(SetAllDAC PRIVATE ${ROOT_LIBRARIES} Threads::Threads)

install(TARGETS ${Targets}
    RUNTIME DESTINATION ${CMAKE_SOURCE_DIR}/../bin
)
add_custom_target(distclean
    COMMAND ${CMAKE_COMMAND} --build . --target clean
    COMMAND ${CMAKE_COMMAND} -E rm -rf ${PROJECT_SOURCE_DIR}/../bin
)