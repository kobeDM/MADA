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

Some scripts (`mada_check_vths.py`, `mada_testout.py`) also reference `ADAHOME` / `ADSW` environment variables that point to a separate ADALM toolset. If you don't use those scripts, you can leave them unset.

### 3. Prepare the config file (`MADA_config.json`)

Create a `MADA_config.json` in your working directory describing the target GigaIwaki boards (IP, Vth, DAC file) and the serial numbers of the ADALM2000 units used for DAQ enable / counter reset. The template is `config/MADA_config_SKEL.json`.

```bash
mada_fetch_config.py
```

If `MADA_config.json` doesn't already exist in the current directory, this copies the template and resolves each entry's ADALM `S/N` to its actual URI using `find_adalm2000.py` (which relies on `bin/FindAdalm`), writing the result back into the file. If `MADA_config.json` already exists, it does nothing.

For each entry under `gigaIwaki`, set:

- `active`: `1` to include the board in DAQ
- `IP`: the board's IP address
- `module`: the MPOD module number that supplies the board's regulator (used for over-current auto-reset)
- `Vth`, `bias`: threshold / bias values
- `DACfile`: path to the DAC file to apply

## Scripts

### Starting / stopping DAQ

- **Start DAQ**
    ```bash
    mada.py [-c config] [-f file_num] [-n event_num] [-d] [--calin IP ch]
    ```
    For every board with `active: 1` in `MADA_config.json`, enables the regulator → sets DAC/Vth/bias → enables latch-up detection once at startup (each step is sent to all boards concurrently). It then repeatedly creates a new `perNNNN/` run directory and collects `file_num` files of `event_num` events each via `MadaIwaki` (controlling DAQ enable / counter reset through the ADALM units), writing a `.info` log for each file, moving on to a new period once `file_num` files have been collected. While the regulator is enabled, a background thread watches the MPOD over-current logs and auto-resets the regulator for any affected board (see below). Ctrl+C stops the run safely, disabling latch-up detection and the regulator on the way out. If a board never replies to a slow-control command, or a `MadaIwaki` process loses its data connection to a board, mada.py stops the run rather than continuing silently.
    - `-c/--config`: config file name (default `MADA_config.json`)
    - `-f/--file_num`: number of files per period (default 512)
    - `-n/--event_num`: number of events per file (default 1000)
    - `-d/--daemon`: detach from the terminal and run in the background, redirecting output to `$MADAHOME/run/<run_dir_name>_<period>.log` — one log file per period, named after the launch directory (e.g. a date-named data directory) and the zero-padded period number, so files never collide even across repeated runs on the same day (PID written to `$MADAHOME/run/mada_daemon.pid`). Stop it with `mada_stop_daq.py` (see below)
    - `--calin IP ch`: use a calibration input, restricting the run to the board at `IP` and specifying the channel (0–127)

- **Stop a background DAQ run**
    ```bash
    mada_stop_daq.py
    ```
    Reads the PID from `$MADAHOME/run/mada_daemon.pid` (written by `mada.py -d`) and sends it SIGTERM, which runs the same shutdown as Ctrl+C (regulator/latch-up detection teardown, `MadaIwaki` processes stopped). If the pidfile is stale (process already gone), it is removed instead.

- **Force-stop DAQ / cleanup**
    ```bash
    mada_daq_killer.py [-c config]
    ```
    Terminates any running `MadaIwaki` processes, updates the latest `.info` file with the final file size and end time, and appends a rate-log entry to `~/rate/YYYYMMDD`. This is also called internally when `mada.py` is interrupted with Ctrl+C.

- **Kill related processes only**
    ```bash
    mada_kill_modules.py   # terminates ad_out / MadaIwaki / mada_daq_killer
    mada_kill_adalms.py    # terminates AdalmControl processes
    ```

### Config, DAC, and Vth

- **Fetch/update the config file (resolve ADALM URIs)**
    ```bash
    mada_fetch_config.py
    ```

- **Apply DAC/Vth/bias to all boards at once**
    ```bash
    mada_set_all_dac.py [config_file] [--calin IP ch]
    ```
    Applies `SetAllDAC` (DAC values, Vth and bias in a single command) to every board listed in `MADA_config.json` (or the given config file) concurrently, and records the applied settings under `config/DAClog/`.

- **Set DAC/Vth/bias on a single board (low level)**
    ```bash
    SetAllDAC [IP] [Vth] [DACfile] [bias] [calin channel]
    # e.g. SetAllDAC 192.168.100.24 8000 DAC_run0006/base_correct.dac 3000
    SetDAC [IP] [DACfile]
    # e.g. SetDAC 192.168.100.24 DAC_run0006/base_correct.dac
    SetVth [IP] [Vth]
    # e.g. SetVth 192.168.100.24 8000
    ```
    `SetAllDAC` is what `mada_set_all_dac.py` calls; `SetDAC`/`SetVth` remain as standalone tools (used e.g. by `mada_run_vth_scan.py`) for setting just one of the two.

- **Check Vth across all boards**
    ```bash
    mada_check_vths.py
    ```
    Fetches the config, emits a test pulse, and runs a Vth scan on each board to confirm the thresholds are as intended (requires the `ADAHOME` environment variable).

- **Toggle ADC bias / AP (regulator) / latch-up detection**
    ```bash
    mada_set_adc_bias.py [-c config]
    mada_set_ap.py {0|1} [-c config]              # disable(0)/enable(1) the regulator
    mada_set_latch_up_detect.py {0|1} [-c config]    # disable(0)/enable(1) latch-up detection
    ```
    Each of these runs `bin/SetADCBias` / `bin/SetAP` / `bin/SetLatchUpDetect` against every board with `active: 1`. `mada_set_ap.py` and `mada_set_latch_up_detect.py` run all boards concurrently and exit non-zero if any board never replies; `mada_set_adc_bias.py` still runs one board at a time. `mada_set_adc_bias.py` is kept as a standalone tool; `mada.py`'s own startup sequence sets bias via `mada_set_all_dac.py` instead (see above) and no longer calls it separately.

- **Regulator over-current auto-reset**
    ```bash
    mada_regulator_autoreset.py [-c config]
    ```
    Watches `Module-<N>_YYYYMMDD.log` under `/nadb/nadb65/status/mpod/regulator_autoreset/` for the MPOD module numbers listed in each `gigaIwaki` entry's `module` field. That log only ever gets a new line appended when the module goes over its current limit, so any new line is itself the trigger: the affected boards' regulators are reset (AP 0→1, via `mada_set_ap.py`'s `target_ip` filter). `mada.py` starts this monitor as a background thread right after enabling the regulator and stops it right before disabling it, so it runs automatically for the lifetime of each DAQ period; run this script directly only for standalone testing.

### Scanning and analysis

- **Vth scan**
    ```bash
    mada_run_vth_scan.py [IP] [Vth low] [Vth high] [Vth step] [-b] [-d DACfile] [-c]
    # e.g. mada_run_vth_scan.py 192.168.100.16 8500 10000 1000
    ```
    Runs the scan with `bin/ScanVth`, then analyzes it with `mada_run_vth_ana.py` (`bin/VthAnalysis` + `rootmacro/ShowVth*.cxx`). Pass `-c` to also apply DAC correction via `rootmacro/DACValueCorrection.cxx`.

- **DAC scan**
    ```bash
    mada_run_dac_scan.py [IP] [Vth]
    ```
    Runs the scan with `bin/DACSurvey` and analyzes it with `bin/DACAnalysis`.

### ADALM2000

- **ADALM discovery (S/N → URI)**
    ```bash
    find_adalm2000.py
    ```

- **ADALM digital output control (DAQ enable / counter reset latch)**
    ```bash
    mada_adalm_control.py [-c config] [-l latch(0/1)] [-i idx(0=DAQ enable,1=counter reset)]
    ```
    Uses `bin/AdalmControl -s [S/N] -l [0/1]` at the low level.

- **Test pulse output**
    ```bash
    mada_testout.py [-u URI] [-f freq(Hz)] [-d]
    ```
    Emits a test pulse via ADSW (`$ADSW/bin/ad_out`); requires the `ADSW` environment variable.

### Monitoring / logging (InfluxDB integration)

- **Data-size (rate) logger**
    ```bash
    mada_log_data_size.py
    ```
    Reads the last line of the rate logs under `~/rate/` and writes it to InfluxDB using the connection info in `config/MADA_logDataSize.json`. The config path can be overridden with the `MADA_LOGSCALER_CONFIG` environment variable.

- **Event-rate logger**
    ```bash
    mada_log_event_rate.py
    ```
    Watches files under the `eventrate_path` from `config/MADA_logEventRate.json` and writes to InfluxDB. The config path can be overridden with the `MADA_LOGEVENTRATE_CONFIG` environment variable.

    Both loggers read `influx` (host/port/username/password/database), `tags`, `retry` (`max_retries`/`initial_backoff`), `interval_seconds`, and `mode` from their config JSON. Edit `config/MADA_logDataSize.json` / `config/MADA_logEventRate.json` to match your environment (host names, database names, etc.).

## Notes

- Build artifacts (`bin/`, `build/`), DAC setting logs (`config/DAClog/`), and Python `__pycache__` directories are all gitignored.
- Files created during a DAQ run (`perNNNN/*.mada` / `*.info`) are written to the run directory, i.e. the current directory from which `mada.py` was launched.
