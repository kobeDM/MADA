# MADA
MiraclueArgonDAQ

## Preparation

NetworkUtil should be cloned in MADA repository

```
$ git clone git@github.com:kobeDM/MADA.git
$ cd MADA
$ git clone git@github.com:kobeDM/NetworkUtil.git
```

- DAQ  
$MADA.py [-n num of events per file] [-m num of files per fir]   
-- config file を準備  (MADA.pyから呼ばれる)  
$MADA_fetch_config.py 
必要に応じて MADA_config.json  を作成

- Vth調整関係  
-- DAC、Vth設定  
--- 全ボードのDAC、Vthを設定、確認  
$MADA_SetAllDAC.py [-c configfile]   
$MADA_checkVths.py  

--- 個々のボードのDACを設定  
$SetDAC IP DACfile  
例 $SetDAC 192.168.100.24 DAC_run0006/base_correct.dac  
--- 個々のボードのVthを設定 
$SetVth IP Vth  
例 $SetDAC 192.168.100.24 8000 
-- DAC, Vth scan  
$MADA_runVthScan.py IP Vth下限 Vth上限 Vth_step  
例　$MADA_runVthScan.py 192.168.100.16 8500 10000 1000  
$MADA_VthScan  
-- DAC値scan
MADA_runDACScan.py  Vth

- その他  
-- $MADA_clockout.py [-f rate(Hz)] [-u URI]  
-- $MADA_DAQenable.py [-d] : DAQ enable出す。 -d optionでenable下げる。　
-- $MADA_counterreset.py : counter reset出す。  




MADA_VthAna          
MADA_runVthAna.py
MADA.py~                      MADA_runVthScan.py
MADA_DACAna          MADA_con             MADA_runVthScan.py~
MADA_DACScan         MADA_iwaki           
       MADA_runDACScan.py   
