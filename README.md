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
| `client/` | DAQ client: HTTP API on the DAQ PC for the web server, and its simulator and tests (see "DAQ client") |
| `tests/` | Tests of the scaler control (`python3 -m pytest tests`) |
| `docs/` | Manuals, update notes, verification records and the client/server specifications (`docs/INDEX.md`) |
| `config/` | Config file templates, DAC files, DAC setting logs (`DAClog/`) |
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

The DAQ client (`client/`) needs more packages; see "DAQ client" below.

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

The script `mada_testout.py` also references `ADAHOME` / `ADSW` environment variables that point to a separate ADALM toolset. If you don't use that script, you can leave them unset.

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
    mada.py [-c config] [-f file_num] [-n event_num] [-d] [--calin IP ch] [--sci]
    ```
    For every board with `active: 1` in `MADA_config.json`, enables the regulator → sets DAC/Vth/bias → enables latch-up detection once at startup only if `general.latch_up_detect` is 1 in `MADA_config.json` (default 0: a run with it enabled leaves the boards in a bad all-hit / no-hit state until they are power cycled) (each step is sent to all boards concurrently). It then repeatedly creates a new `perNNNN/` run directory and collects `file_num` files of `event_num` events each via `MadaIwaki` (controlling DAQ enable / counter reset through the ADALM units), writing a `.info` log for each file, moving on to a new period once `file_num` files have been collected. The MPOD over-current auto-reset is a separate monitor process (`mada_regulator_autoreset.py`, see below); `mada.py` makes sure it is running before the regulator is switched on and at every file boundary, and stops the DAQ if it cannot be started. Ctrl+C stops the run safely, disabling the regulator (and latch-up detection, if it was enabled) on the way out. If a board never replies to a slow-control command, mada.py stops the run rather than continuing silently. If a `MadaIwaki` process dies while a file is being acquired (e.g. it loses its data connection to a board), that file is kept, marked invalid (`runinfo.valid = false` and `invalid_reason` in every `.info`, `kind=file_invalid` in `warnings.log`) and redone for all boards under the next file number; invalid files do not count toward `file_num`, and 3 in a row stop the DAQ. Skip the files with `valid = false` in the analysis.
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
| `mada_sci.py` | the SCI mode: one `AdalmAnalogIn` process per file (start, check, stop) |
| `mada_scan.py`, `mada_scan_session.py`, `mada_scan_board.py`, `mada_scan_tools.py`, `mada_scan_progress.py`, `mada_scan_replot.py` | DAC/Vth scan: entry point, session (power, DAQ enable, parallel boards), one board's correction, scan binaries, progress bars, redo of the fits |
| `mada_run_logger.py` | `perNNNN/` directories, `.info` files, rate log |
| `mada_run_state.py` | `run/mada_run.json`, `mada_progress.json`, `mada_last_exit.json`: what the DAQ is doing and why it stopped, for the LV-reset monitor and the DAQ client |
| `mada_scaler.py` | the scaler (`runScaler` on the Zybo): start per period over ssh, check after every file, stop |
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
    `SetAllDAC` is what `mada_set_all_dac.py` calls; `SetDAC`/`SetVth` remain as standalone tools for setting just one of the two.

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

- **DAC/Vth correction (noise-only scans, all boards in parallel)**
    ```bash
    mada_scan.py [-c config] [-b board|IP ...] [-o outdir] [-n events] [--vth-events N] [-t timeout] [-s settle]
                 [--level L] [--dac-level L] [--metric occupancy|rate] [--window-hit W] [--window-nohit W]
                 [--step S] [--max-iter N] [--slope-dv DV] [--target config|median]
    # e.g. mada_scan.py -c MADA_config.json -n 300 --vth-events 2000 -t 25 --step 20
    ```
    Needs no DAQ running and the external trigger running; the hits are the noise crossing the threshold. Boards whose regulator (AP) is off are switched on (with the config's Vth/DAC/bias, and the autoreset monitor) and switched off again at the end; boards that were already on stay on. It raises DAQ enable for the session, shows one progress bar per board (stage, points done, elapsed time, estimate of the time left; redrawn in place on a terminal, one status line a minute in a log file), and for every board (in parallel):
    1. DAC scan at the board's working Vth (DAC 0-63 on all channels at once) -> the DAC where each channel reaches the alignment level at that Vth (`ScanAcquire`, `ScanFit`, `ScanCorrect dac`).
    2. A second DAC scan at Vth + `--slope-dv` (default 200) -> the measured Vth counts per DAC count (`ScanCorrect slope`); falls back to 52 with a warning if the result is not plausible. The DAC scan also tells on which side of the Vth scale the hits are (cathode boards: low Vth, anode boards: high Vth).
    3. Vth scans verify the result: from the working Vth `--window-hit` (default 300) towards the hits and `--window-nohit` (default 300) towards the no-hit side, so that the whole noise edge of every channel is covered. `ScanCorrect refine` moves the DAC of channels more than 0.6 DAC off the target; the scan is repeated until no value changes or `--max-iter` (default 5) refinements were made.

    **Alignment.** The scan is done at the `Vth` of the board's config entry, which becomes the working point the channels are aligned to. The channels are aligned not at the center of their noise transition (hit rate 50%, where the noise hits all the time) but at the edge where the noise vanishes: where the fraction of events with a hit (`--metric occupancy`, default; `rate` counts clocks with a hit instead) has risen to `--level` (default 0.005) of the whole transition, coming from the no-hit side (`--dac-level`, default 0.05, for the DAC scans, which have fewer events and only give the start). The position is read from the data by interpolation, because the tail of the noise distribution is heavier than an error function. `--level 0.5 --metric rate` aligns the fitted centers. The tail needs many events (a level of 0.005 is 10 events at 2000), so give the Vth scans more with `--vth-events` (the points time out at `-t`). The Vth in the config is where the channels end up aligned; run the DAQ a margin beyond it (towards fewer hits) to have no noise at all. For a first calibration (no DAC file tuned for the board yet) set `Vth` to 8000 in the config before scanning.

    **Data and results.** Every point takes `-n` events or at most `-t` seconds (a point that times out is kept with the events it got and reported; a scan with no event at all stops with an error). Channels that never hit (dead) or always hit (stuck), or that show no transition, are not fitted, keep the DAC of the board's config DACfile, and are listed in the summary. The hit statistics count every event, including the ones without hit data. Results go to `scan_runNNNN/<board>/` (scan data, `fit_result.csv/.root`, `fit_summary.png`, `Vthcheck.png`, `dac_N.dac`, `summary.json`) and `scan_runNNNN/<board>.dac` is the corrected DAC file; **copy it into the config's `DACfile` by hand**. After the scan every board gets its configured Vth, DAC values and bias again.

- **Redo the fits and plots of finished scans**
    ```bash
    mada_scan_replot.py scan_runNNNN [scan_runMMMM ...]
    ```
    Runs `ScanFit` again on the saved data of every board (no board access). The scan plots are `vth_scan_N/Vthcheck.png` (hit rate vs channel and Vth, red line at the working Vth) and `dac_scan_N/DACcheck.png`.

- **Single scans (low level)**
    ```bash
    ScanAcquire [IP] vth [outdir] [start] [end] [step] -d [DAC file] [-n events] [-t sec] [-s settle]
    ScanAcquire [IP] dac [outdir] [start] [end] [step] -v [Vth] [-n events] [-t sec] [-s settle]
    ScanFit [outdir] {vth|dac} [target [level [rate|occupancy]]]   # also reads the data of the removed ScanVth/DACSurvey
    ScanCorrect {dac|slope|refine} ...
    ```

### SCI mode: PMT pulses against the DAQ trigger

```bash
mada.py --sci [other options]
```
With `--sci`, another ADALM2000 (the `SCI` section of the config, never one of the `MADALM_n` of the DAQ) records, for every trigger of the DAQ, the time of the PMT pulses relative to the trigger edge. Both signals are discriminated NIM signals (negative, about -0.8 V) on the analog inputs, terminated with 50 ohm, input range `low` (+-2.5 V). The ADALM triggers on the DAQ trigger (`SCI.trigger`, threshold only) and keeps `pre_trigger_samples` (default 8000 = 80 us, at most 8192) of the buffer before it, since the PMT comes first; the pulses of the PMT channel in the whole buffer are found in software (crossing of the threshold, interpolated between the 10 ns samples; gaps of two samples or less do not split a pulse).

```json
"SCI": {
    "active": 1, "S/N": "<serial of the ADALM>",
    "channels": { "pmt": 1, "trigger": 2 },
    "trigger": { "threshold_V": -0.4, "edge": "falling" },
    "pmt": { "threshold_V": -0.4, "edge": "falling" },
    "range": "low", "buffer_samples": 8192, "pre_trigger_samples": 8000, "save_waveform": 0
}
```
`mada.py --sci` checks the section before anything is started (the ADALM must differ from the DAQ's, the channels must be 1 and 2, the thresholds within the range, the pre-trigger length within 8192 with 100 samples left after the trigger). One `bin/AdalmAnalogIn` runs per file, armed before the readers start and stopped after they end; its start is serialized with the other ADALM calls (`run/adalm.lock`). If it cannot start, dies, or sees no trigger for 30 s while DAQ enable is up, the DAQ stops with an error (and the reason goes into `warnings.log`).

Per file the period directory gets `SCI_NNNN.root` (tree `trigger`, one entry per trigger: `seq`, `t_epoch` (PC clock, roughly matches the DAQ files), `trig_ns`, `n_pmt`, and per PMT pulse `pmt_dt` [ns, negative: before the trigger], `pmt_amp` [V], `pmt_width` [ns]; `flags`: 1 = no trigger edge found, 2 = a sample at the range limit; with `save_waveform` also `wave_pmt`, `wave_trig` [V]; the object `meta` holds the settings) and `SCI_NNNN.info`. The analysis of `pmt_dt` (drift time) is done in the analyzer, not here; the file format is described in `docs/manuals/2026-11-10.md`. `bin/AdalmAnalogIn --simulate [Hz]` produces the same files from simulated signals, to test without an ADALM.

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

### Scaler (runScaler on the Zybo)

With `SCALER.active` = 1 in `MADA_config.json`, `mada.py` runs the scaler (`runScaler`, MAZYSCA_SW) over ssh together with the DAQ. `runScaler <dir> <period>` serves one period and writes `<dir>/perNNNN`, one line per falling edge of DAQ enable, so `mada.py`:

1. checks the section and the ssh connection before anything is started (`Error:` and exit code 1 otherwise), and stops a `runScaler` left over from an earlier run when the session starts;
2. starts `runScaler <remote_output_root>/<run> <period>` for every period (`output_root` is the same directory as seen from this PC, `/nadb61/scaler`; the Zybo mounts it at `/nadb/nadb61/scaler`), while DAQ enable is low and before the first file; the run is the name of the launch directory, as for the log files, and an existing `perNNNN` is never overwritten;
3. checks after every file that the scaler recorded a line for it (the output directory is shared with the Zybo, so no ssh is needed);
4. stops it after the last file of the period, and on every exit path (after DAQ enable is lowered and the boards are powered down).

If the scaler cannot be started, does not record a file, or cannot be stopped, the DAQ stops with an error. `run/mada_scaler.json` holds its state (`running`, `stopped`, `failed`); the DAQ client reports it as `monitor.scaler`. Run `ssh <host>` once by hand first so that the host key is known (ssh runs with `BatchMode`). Tests: `python3 -m pytest tests` (uses a fake `ssh`; run it apart from `client/tests`, both set their own `MADAHOME`).

## DAQ client (HTTP API for the web server)

`client/` is an HTTP API server that runs on the DAQ PC so that a web server on another PC can start and stop the DAQ and watch it (specification: [docs/specs/2026-11-12.md](docs/specs/2026-11-12.md) for the API, [docs/specs/2026-11-12_2.md](docs/specs/2026-11-12_2.md) for the client). It only runs `mada.py -d`, sends it SIGTERM and reads the files MADA writes; the DAQ keeps running if the client stops.

```bash
pip install -r client/requirements.txt
cp config/MADA_client_SKEL.json config/MADA_client.json   # allowed_servers, token_file (mode 600), data_root
python3 client/mada_client.py [-c settings.json] [--port N]
python3 client/mada_client.py --simulate                  # simulated DAQ in a temporary MADAHOME, no hardware
python3 -m pytest client/tests                            # needs pytest and httpx
```

`client/mada-client.service` is an example systemd user unit. The simulator (`--simulate`, options `--sim-file-sec`, `--sim-fail-after`, `--sim-lag`, `--sim-invalid-file`) is for developing the web server without hardware. `mada.py` publishes `run/mada_run.json`, `run/mada_progress.json` and `run/mada_last_exit.json` for the client.

## Notes

- Build artifacts (`bin/`, `build/`), DAC setting logs (`config/DAClog/`), and Python `__pycache__` directories are all gitignored.
- Files created during a DAQ run (`perNNNN/*.mada` / `*.info` / `warnings.log`) are written to the run directory, i.e. the current directory from which `mada.py` was launched.
- `perNNNN/warnings.log` collects, for the whole period, what the readers report on stderr plus the reader restarts and the error that stopped the DAQ. Tab-separated: epoch s, ISO time, file number, source (board or `DAQ`), message. `MadaIwaki` writes timing warnings with the wall-clock time `t=` (epoch s) of the event: `kind=write_slow` (writing to disk took `sec`: PC side), and an `INFO ... kind=summary` line when a file is complete. The DAQ itself adds `kind=board_lag` / `board_lag_end` (a board lacks an event the other boards already have for 0.2 s) and `kind=file_invalid` (a reader died; see below). The reporting threshold is `MadaIwaki -t <sec>` (default 0.2 s). The LV-reset monitor (source `LV`) appends to the same file while a DAQ is running (`kind=over_limit` with the MPOD line, `lv_reset_start`, per board `ap_off` / `ap_on` (or `ap_on_failed`, `ap_left_off`, `ap_off_skip`), `veto_assert` / `veto_release`, `lv_reset_end`), so a gap can be matched with an LV reset too. The DAQ publishes the period and file it is writing in `run/mada_run.json`; with no DAQ running, the monitor writes nothing to any period. Use it to tell the cause of missing trigger IDs: match the `t=` of a stall with the time of the gap (`.info` start + clock counter, 100 us units).
