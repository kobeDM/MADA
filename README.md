# MADA
MiraclueArgonDAQ  
$MADA.py [-n num of events per file] [-m num of files per fir]   
edit MADA_config.json  
- Vth調整関係  
-- DAC設定  
--- config fileを用意して全ボードのDACを設定  
$MADA_SetDAC.py [-c configfile]   
--- 個々のボードのDACを設定  
$SetDAC IP DACfile  
例 $SetDAC 192.168.100.24 DAC_run0006/base_correct.dac  
-- Vth scan  
$MADA_runVthScan.py IP Vth下限 Vth上限 Vth_step  
例　$MADA_runVthScan.py 192.168.100.16 8500 10000 1000  
MADA_VthScan  
-- DAC値scan
MADA_runDACScan.py  Vth


MADA.py              
MADA_VthAna          
MADA_runVthAna.py
MADA.py~                      MADA_runVthScan.py
MADA_DACAna          MADA_con             MADA_runVthScan.py~
MADA_DACScan         MADA_iwaki           
       MADA_runDACScan.py   
