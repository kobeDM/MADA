#Target = read_CtrlMem SetDAC SetVth DAC_Survey GigaDAQ ScanVth DAQcheck
Target =  MADA_DACAna MADA_VthAna
#GigaDAQ_2
Module = RBCP SiTCP TCPclient 

ObjSuf = .o
SrcSuf = .cxx

# Compiler flags
CFLAGS = -Wall -O2 -c
CFLAGS += $(shell root-config --cflags)
LDFLAGS	= $(shell root-config --ldflags)

LIBS	= $(shell root-config --libs)
LIBS   += $(shell root-config --glibs)

# Debug flags
#CFLAGS += -g

#LDFLAGS += -all_load
#LDFLAGS += -g

TargetSrc = $(Target:%=%$(SrcSuf))
TargetObj = $(Target:%=%$(ObjSuf))
ModuleSrc = $(Module:%=%$(SrcSuf))
ModuleObj = $(Module:%=%$(ObjSuf))

all	: ../bin/$(Target)

$(Target): $(TargetObj) $(ModuleObj)
	$(CXX) -o ../bin/$@ $@.o $(ModuleObj)  $(LIBS) $(LDFLAGS)

.cxx.o	:
	$(CXX) $(CFLAGS) -c -o $@ $<

.SUFFIXES: .o .cxx

clean	:
	rm -f *.o
	rm -f *~
	rm -f $(Target)
