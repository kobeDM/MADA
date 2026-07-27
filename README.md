# MADA (MiraclueArgonDAQ)

DAQ and calibration tools for the GigaIwaki (v3.1) readout board. The project consists of low-level control binaries written in C++ (`source/` → built into `bin/`) and Python scripts (`scripts/`) that orchestrate them for day-to-day operation.
This branch is tuned for GigaIwaki v3.1.

## Directory layout

| Directory | Contents |
| --- | --- |
| `source/` | C++ sources (DAQ core, DAC/Vth setting, ADALM2000 control, etc.) |
| `include/` | Shared headers (SiTCP/RBCP communication, ADALM utilities, etc.) |
| `bin/` | Install destination for built executables (gitignored) |
| `build/` | CMake build directory (gitignored) |
| `scripts/` | Python scripts for operation and automation |
| `config/` | Config file templates, DAC files, DAC setting logs (`DAClog/`) |
| `rootmacro/` | CERN ROOT macros for Vth/DAC analysis |
| `setup.sh` | Sets environment variables and `PATH` |

## Requirements

- CMake 3.1.3 or later, a C++11-capable compiler
- [CERN ROOT](https://root.cern/) (`RIO`, `Net` components; `ROOTSYS` environment variable must be set)
- [libm2k](https://github.com/analogdevicesinc/libm2k) (for ADALM2000 control)
- Python 3
- Python packages: `psutil` (process management), `influxdb` (only needed for the scripts that push data/event rates to InfluxDB)

```bash
pip install psutil influxdb
```

## Setup

### 1. Build

The C++ executables are built from `source/CMakeLists.txt` into `build/` and installed into `bin/`.

```bash
mkdir -p build && cd build
cmake ../source
make
make install    # executables are installed into bin/
```

### 2. Set environment variables

Sourcing `setup.sh` from the repository root sets `MADAHOME` (the path to this repository) and adds `scripts/` and `bin/` to `PATH`. Every script relies on `MADAHOME` to locate the other executables/scripts it calls, so make sure to source it before running anything.

```bash
source setup.sh
```

Run `source setup.sh` from the working directory where you'll launch DAQ (i.e. where the `per0000/` run directories will be created), or add it to your `.bashrc` so it's always available.

Some scripts (`MADA_checkVths.py`, `MADA_testout.py`) also reference `ADAHOME` / `ADSW` environment variables that point to a separate ADALM toolset. If you don't use those scripts, you can leave them unset.

### 3. Prepare the config file (`MADA_config.json`)

Create a `MADA_config.json` in your working directory describing the target GigaIwaki boards (IP, Vth, DAC file) and the serial numbers of the ADALM2000 units used for DAQ enable / counter reset. The template is `config/MADA_config_SKEL.json`.

```bash
MADA_fetch_config.py
```

If `MADA_config.json` doesn't already exist in the current directory, this copies the template and resolves each entry's ADALM `S/N` to its actual URI using `findADALM2000.py` (which relies on `bin/FindAdalm`), writing the result back into the file. If `MADA_config.json` already exists, it does nothing.

For each entry under `gigaIwaki`, set:

- `active`: `1` to include the board in DAQ
- `IP`: the board's IP address
- `Vth`, `bias`: threshold / bias values
- `DACfile`: path to the DAC file to apply

## Scripts

### Starting / stopping DAQ

- **Start DAQ**
    ```bash
    MADA.py [-c config] [-f file_num] [-n event_num] [--calin IP ch]
    ```
    Creates a new `perNNNN/` run directory and, for every board with `active: 1` in `MADA_config.json`, runs the following in sequence: enable the regulator → set DAC/Vth → enable latch-up detection → collect `file_num` files of `event_num` events each via `MADA_iwaki` (controlling DAQ enable / counter reset through the ADALM units) → write a `.info` log for each file. Ctrl+C stops the run safely, disabling latch-up detection and the regulator on the way out.
    - `-c/--config`: config file name (default `MADA_config.json`)
    - `-f/--file_num`: number of files per period (default 512)
    - `-n/--event_num`: number of events per file (default 1000)
    - `--calin IP ch`: use a calibration input, restricting the run to the board at `IP` and specifying the channel (0–127)

- **Force-stop DAQ / cleanup**
    ```bash
    MADA_DAQkiller.py [-c config]
    ```
    Terminates any running `MADA_iwaki` / `MADA_DAQenable.py` processes, updates the latest `.info` file with the final file size and end time, and appends a rate-log entry to `~/rate/YYYYMMDD`. This is also called internally when `MADA.py` is interrupted with Ctrl+C.

- **Kill related processes only**
    ```bash
    MADA_killmodules.py   # terminates MADA_DAQenable / ad_out / MADA_iwaki / MADA_DAQkiller
    MADA_killadalms.py    # terminates AdalmControl processes
    ```

### Config, DAC, and Vth

- **Fetch/update the config file (resolve ADALM URIs)**
    ```bash
    MADA_fetch_config.py
    ```

- **Apply DAC/Vth to all boards at once**
    ```bash
    MADA_SetAllDAC.py [config_file] [--calin IP ch]
    ```
    Applies `SetDAC` / `SetVth` to every board listed in `MADA_config.json` (or the given config file) and records the applied settings under `config/DAClog/`.

- **Set DAC/Vth on a single board (low level)**
    ```bash
    SetDAC [IP] [DACfile]
    # e.g. SetDAC 192.168.100.24 DAC_run0006/base_correct.dac
    SetVth [IP] [Vth]
    # e.g. SetVth 192.168.100.24 8000
    ```

- **Check Vth across all boards**
    ```bash
    MADA_checkVths.py
    ```
    Fetches the config, emits a test pulse, and runs a Vth scan on each board to confirm the thresholds are as intended (requires the `ADAHOME` environment variable).

- **Toggle ADC bias / AP (regulator) / latch-up detection**
    ```bash
    MADA_SetADCBias.py [-c config]
    MADA_SetAP.py {0|1} [-c config]              # disable(0)/enable(1) the regulator
    MADA_SetLatchUpDetect.py {0|1} [-c config]    # disable(0)/enable(1) latch-up detection
    ```
    Each of these runs `bin/SetADCBias` / `bin/SetAP` / `bin/SetLatchUpDetect` against every board with `active: 1`.

### Scanning and analysis

- **Vth scan**
    ```bash
    MADA_runVthScan.py [IP] [Vth low] [Vth high] [Vth step] [-b] [-d DACfile] [-c]
    # e.g. MADA_runVthScan.py 192.168.100.16 8500 10000 1000
    ```
    Runs the scan with `bin/ScanVth`, then analyzes it with `MADA_runVthAna.py` (`bin/Vth_Analysis` + `rootmacro/ShowVth*.cxx`). Pass `-c` to also apply DAC correction via `rootmacro/DACValueCorrection.cxx`.

- **DAC scan**
    ```bash
    MADA_runDACScan.py [IP] [Vth]
    ```
    Runs the scan with `bin/DAC_Survey` and analyzes it with `bin/DAC_Analysis` (`runDACAna.py` handles visualization via `rootmacro/ShowDAC*.cxx`).

### ADALM2000

- **ADALM discovery (S/N → URI)**
    ```bash
    findADALM2000.py
    # also importable as a library: get_uri_by_serial(serial)
    ```

- **ADALM digital output control (DAQ enable / counter reset latch)**
    ```bash
    MADA_adalm_control.py [-c config] [-l latch(0/1)] [-i idx(0=DAQ enable,1=counter reset)]
    ```
    Uses `bin/AdalmControl -s [S/N] -l [0/1]` at the low level.

- **Test pulse output**
    ```bash
    MADA_testout.py [-u URI] [-f freq(Hz)] [-d]
    ```
    Emits a test pulse via ADSW (`$ADSW/bin/ad_out`); requires the `ADSW` environment variable.

### Monitoring / logging (InfluxDB integration)

- **Data-size (rate) logger**
    ```bash
    MADA_logDataSize.py
    ```
    Reads the last line of the rate logs under `~/rate/` and writes it to InfluxDB using the connection info in `config/MADA_logDataSize.json`. The config path can be overridden with the `MADA_LOGSCALER_CONFIG` environment variable.

- **Event-rate logger**
    ```bash
    MADA_logEventRate.py
    ```
    Watches files under the `eventrate_path` from `config/MADA_logEventRate.json` and writes to InfluxDB. The config path can be overridden with the `MADA_LOGEVENTRATE_CONFIG` environment variable.

    Both loggers read `influx` (host/port/username/password/database), `tags`, `retry` (`max_retries`/`initial_backoff`), `interval_seconds`, and `mode` from their config JSON. Edit `config/MADA_logDataSize.json` / `config/MADA_logEventRate.json` to match your environment (host names, database names, etc.).

## Notes

- Build artifacts (`bin/`, `build/`), DAC setting logs (`config/DAClog/`), and Python `__pycache__` directories are all gitignored.
- Files created during a DAQ run (`perNNNN/*.mada` / `*.info`) are written to the run directory, i.e. the current directory from which `MADA.py` was launched.
