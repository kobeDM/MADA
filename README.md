# MADA (MiraclueArgonDAQ)
# Usage
- DAQ  
    ```
    $ MADA.py [-n file size (Mbyte)]
    ```

- Fetch config file
    ```
    $ MADA_fetch_config.py 
    ```

- DAC、Vth setting  
    - Set All DAC files
       ```
       $ MADA_SetAllDAC.py [-c configfile]   
       $ MADA_checkVths.py  
       ```

    - Set each DAC file
       ```
       $ SetDAC [IP] [DACfile]
       # e.g $ SetDAC 192.168.100.24 DAC_run0006/base_correct.dac
       ```
    - Set each Vth value
       ```
       $ SetVth [IP] [Vth]  
       # e.g. $ SetDAC 192.168.100.24 8000 
       ```
- Vth scan  
    ```
    $ MADA_runVthScan.py [IP] [Vth lowwer] [Vth upper] [Vth step]  
    # e.g. $ MADA_runVthScan.py 192.168.100.16 8500 10000 1000  
    ```
- DAC scan  
    ```
    $ MADA_runDACScan.py  [Vth]
    ```

- Others
    - Output clock
       ```
       $MADA_clockout.py [-f rate(Hz)] [-u URI]  
       ```
    - Output DAQ enable
       ```
       $ MADA_DAQenable.py [-d down]
       ```
    - Output counter reset
       ```
       $MADA_counterreset.py
       ```
