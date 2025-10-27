# MADA
MiraclueArgonDAQ

Upgraded DAQ system (ver. 2025 Autumn)

## Preparation

For all server and clients, NetworkUtil should be cloned in MADA repository
```
$ git clone git@github.com:kobeDM/MADA.git
$ cd MADA
$ git clone git@github.com:kobeDM/NetworkUtil.git
```

### MADA (Client for integration)

After git clone, make and move "run" directory and edit a config file
```
$ cd /home/msgc/miraclue/run/30LAuPIC_2/
$ mkdir yyyymmdd && cd yyyymmdd
$ cp ${MADAPATH}/config/MADA_config_SKEL.json ./MADA_config.json
$ emacs MADA_config.json
```

### MAQS (DAQ server)

In MADA directory, make a build directory and build the project
```
$ mkdir build && cd build
$ cmake ../source/MAQS
$ make && make install
```

Then start MAQS's server.
```
$ cd /home/msgc/miraclue/data/30LAuPIC_2/yyyymmdd/
$ MAQS.py -a 10.37.0.18X -p 900X
(if you need to start MAQS1 server, do above commands with X = 1)
```

### MACARON (Control server)

In MADA directory, make a build directory and build the project
```
$ mkdir build && cd build
$ cmake ../source/MACARON
$ make && make install
```

Then start MAQS's server.
```
$ cd /home/msgc/miraclue/scaler/
$ MACARON.py -a 10.37.0.178 -p 9100
```

### MASCOT (Slow control and monitor server)

Enter MASCOT then just do below command in the home directory
```
$ MASCOT.py -a 10.37.0.214 -p 9200
```

## Operation

Do below scripts in MAMA client.
Do not forget editing MADA_config.json for each execution

- DAQ  
```
$ MADA.py
```

- Set Vth and DAC   
```
$ MADA_SetVthDAC.py
```

-- Set Vth or DAC parameter for each GBKB
```
$ SetDAC [IP] [DAC file]  
$ SetVth [IP] [Vth value]  
```

-- Vth and scans 
```
$ MADA_runVthScan.py  
$ MADA_runDACScan  
```
