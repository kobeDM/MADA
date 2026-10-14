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
    For every board with `active: 1` in `MADA_config.json`, enables the regulator → sets DAC/Vth/bias → enables latch-up detection once at startup only if `general.latch_up_detect` is 1 in `MADA_config.json` (default 0: a run with it enabled leaves the boards in a bad all-hit / no-hit state until they are power cycled) (each step is sent to all boards concurrently). It then repeatedly creates a new `perNNNN/` run directory and collects `file_num` files of `event_num` events each via `MadaIwaki` (controlling DAQ enable / counter reset through the ADALM units), writing a `.info` log for each file, moving on to a new period once `file_num` files have been collected. The MPOD over-current auto-reset is a separate monitor process (`mada_regulator_autoreset.py`, see below); `mada.py` makes sure it is running before the regulator is switched on and at every file boundary, and stops the DAQ if it cannot be started. Ctrl+C stops the run safely, disabling the regulator (and latch-up detection, if it was enabled) on the way out. If a board never replies to a slow-control command, or a `MadaIwaki` process loses its data connection to a board, mada.py stops the run rather than continuing silently.
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

### DAQ-flow modules (one responsibility per file)

`scripts/mada.py` is only the entry point (arguments, config check, daemonizing); the rest of the DAQ flow is split as follows.

| File | Responsibility |
|------|----------------|
| `mada_daq_session.py` | one session: power up, acquire period after period, guarded shutdown |
| `mada_file_cycle.py` | one file: start readers, reset counters, DAQ enable, wait, close |
| `mada_gigaiwaki.py` | the MadaIwaki readers (start with per-board restart, stop) |
| `mada_progress.py` | live per-board event counts |
| `mada_run_logger.py` | `perNNNN/` directories, `.info` files, rate log |
| `mada_config.py` / `mada_adalm_roles.py` | config access and validation / ADALM roles and DIO masks |
| `mada_adalm_runner.py` / `mada_adalm_control.py` | run `AdalmControl` with lock and timeout / its command line |
| `mada_process.py` | find and stop processes by program name |
| `mada_errors.py` | `MadaError`, the base of all errors that stop a DAQ run |
| `mada_autoreset_ctl.py`, `mada_regulator_monitor.py`, `mada_regulator_autoreset.py`, `mada_software_veto.py`, `mada_ap_state.py` | LV-reset monitor (start-up guarantee, logic, command line), software veto, AP state |

Behaviour worth knowing: the config is validated (boards, DAC files, ADALM roles and masks) before anything is started or daemonized, and any failure stops the DAQ with a message and a non-zero exit code. A reader (`MadaIwaki`) that fails while starting, typically a refused or dropped TCP connection, is restarted on its own up to three times; DAQ enable and the counter reset are only sent, to all boards in one command each, after every reader is up. A reader that dies after DAQ enable stops the DAQ. Process stopping matches the program name exactly, so unrelated processes whose command line merely mentions `MadaIwaki` are left alone.

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

- **Regulator over-current auto-reset (monitor)**
    ```bash
    mada_regulator_autoreset.py -d [-c config] [--idle-exit SEC]   # start in the background (log: run/mada_autoreset.log)
    mada_regulator_autoreset.py --stop                             # stop it
    ```
    You normally do not start it by hand: `run_set_ap(io=1)` (used by `mada.py`, `mada_encoder_power.py` and `mada_set_ap.py`) starts it before the regulator is switched on, and restarts it if it was started with another config. It runs independently of `mada.py`, so it keeps protecting boards powered on via `mada_encoder_power.py` / `mada_set_ap.py`, and exits by itself once every active board has had AP off for `--idle-exit` seconds (default 600; 0 = never). Directly calling the `bin/SetAP` binary bypasses this. It watches `Module-<N>_YYYYMMDD.log` under `/nadb/nadb65/status/mpod/regulator_autoreset/` for the MPOD module numbers listed in each `gigaIwaki` entry's `module` field. That log only ever gets a new line appended when the module goes over its current limit, so any new line is itself the trigger: the affected boards' regulators are reset (AP 0→1) and the software veto is asserted meanwhile. A board whose AP is off (register 0xf1) is skipped, so it is never switched on by mistake. The config is read once at start. Only one instance runs (`run/mada_autoreset.lock`, `run/mada_autoreset.pid`).

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
    mada_adalm_control.py [-c config] [-l latch(0/1)] [-i idx(0=DAQ enable,1=counter reset,2=software veto)] [-w width]
    ```
    Uses `bin/AdalmControl -s [S/N] -l [0/1]` at the low level. All lines of one call (a role's `DIO_mask`) change on the same sample via a short buffer (not one `setValueRaw` per line), and other lines keep their level. `-m [mask]` selects the DIO lines (bit i = Di, default 0xFFFF); `MADALM_n.DIO_mask` in the config sets it per role, so DAQ enable (D0-D4) and counter reset (D8-D11) can share one ADALM by giving both the same S/N. `AdalmControl` exits non-zero on libm2k errors; the wrapper retries up to 3 times and then raises `AdalmError`, which makes `mada.py` stop the DAQ safely.

- **Software veto (D12, active high) to the scaler**
    ```bash
    mada_software_veto.py [1/0] [-c config]     # manual assert / release (testing only)
    ```
    Defined by `MADALM_2` (same S/N as MADALM_0, `DIO_mask` 0x1000). The auto-reset monitor is the sole owner of D12: it drives it low at start and on exit, asserts it in parallel with the LV reset (AP off), and releases it 0.5 s after the last AP on. Assert/release times go to `run/veto.log`. If a release fails, the monitor retries every 10 s and records `failed` in `run/veto.state`; `mada.py` checks that file at each file boundary and stops safely. All `AdalmControl` calls through `run_adalm_control` are serialized with a file lock (`run/adalm.lock`). Add a pull-down on the scaler input so a floating line never reads as veto. If the monitor is killed with SIGKILL, D12 can stay high until it is restarted.

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
- Files created during a DAQ run (`perNNNN/*.mada` / `*.info` / `warnings.log`) are written to the run directory, i.e. the current directory from which `mada.py` was launched.
- `perNNNN/warnings.log` collects, for the whole period, what the readers report on stderr plus the reader restarts and the error that stopped the DAQ. Tab-separated: epoch s, ISO time, file number, source (board or `DAQ`), message. `MadaIwaki` writes timing warnings with the wall-clock time `t=` (epoch s) of the event: `kind=recv_wait` (the board sent nothing for `sec`, much longer than the usual interval: board or network side), `kind=write_slow` (writing to disk took `sec`: PC side), and an `INFO ... kind=summary` line when a file is complete. The reporting threshold is `MadaIwaki -t <sec>` (default 0.2 s). The LV-reset monitor (source `LV`) appends to the same file while a DAQ is running (`kind=over_limit` with the MPOD line, `lv_reset_start`, per board `ap_off` / `ap_on` (or `ap_on_failed`, `ap_left_off`, `ap_off_skip`), `veto_assert` / `veto_release`, `lv_reset_end`), so a gap can be matched with an LV reset too. The DAQ publishes the period and file it is writing in `run/mada_run.json`; with no DAQ running, the monitor writes nothing to any period. Use it to tell the cause of missing trigger IDs: match the `t=` of a stall with the time of the gap (`.info` start + clock counter, 100 us units).
