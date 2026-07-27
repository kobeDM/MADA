#! /usr/bin/env python3

"""
Scaler watcher that reads last-line rates and writes to InfluxDB.
Configuration is read from a JSON config file.
"""

import os
import time
import json
import logging
import datetime
from pathlib import Path
from influxdb import InfluxDBClient

# Load configuration
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "MADA_logDataSize.json"
config_path = os.environ.get("MADA_LOGSCALER_CONFIG", str(DEFAULT_CONFIG))
with open(config_path, "r") as cf:
    cfg = json.load(cf)

# Expand and normalize rate path
RATEPATH = os.path.expanduser(cfg.get("rate_path", "~/rate/"))

# Setup InfluxDB client from config
influx_cfg = cfg.get("influx", {})
client = InfluxDBClient(
    host=influx_cfg.get("host", "localhost"),
    port=int(influx_cfg.get("port", 8086)),
    username=influx_cfg.get("username"),
    password=influx_cfg.get("password"),
    database=influx_cfg.get("database")
)

# Tags to attach to each point
TAGS = cfg.get("tags", {})

# Retry policy
RETRY_CFG = cfg.get("retry", {})
MAX_RETRIES = int(RETRY_CFG.get("max_retries", 3))
INITIAL_BACKOFF = float(RETRY_CFG.get("initial_backoff", 1.0))

# Polling interval and mode
INTERVAL_SECONDS = int(cfg.get("interval_seconds", 10))
MODE = cfg.get("mode", "latest").lower()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MADA_logScaler")


def process_file(target_filepath, index=None, total=None):
    """Read last line from a file, parse rates, and send to InfluxDB with retries.

    Returns True on success, False on failure.
    """
    try:
        with open(target_filepath, "r") as f:
            lines = f.readlines()
            if not lines:
                logger.debug("File %s is empty", target_filepath)
                return False
    except Exception as e:
        logger.exception("Failed to read file %s: %s", target_filepath, e)
        return False

    json_data = []
    valid_lines = 0
    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 7:
            logger.warning("Unexpected line format in %s line %d: %s", target_filepath, line_no, line)
            continue

        # Parse expected columns (robust to whitespace)
        try:
            startunixtime = float(parts[1])
            realrate_cathode = float(parts[5])
            realrate_anode = float(parts[6])
        except Exception:
            logger.exception("Failed to parse numeric fields from %s line %d: %s", target_filepath, line_no, line)
            continue

        scalertime = datetime.datetime.utcfromtimestamp(startunixtime)
        json_data.append(
            {
                "measurement": "file_size",
                "tags": TAGS,
                "time": scalertime.isoformat() + "Z",
                "fields": {
                    "trigger_rate_real_anode": realrate_anode,
                    "trigger_rate_real_cathode": realrate_cathode,
                },
            }
        )
        valid_lines += 1
        logger.info(
            "Parsed line %d/%d from %s: cathode=%s, anode=%s",
            line_no,
            len(lines),
            target_filepath,
            realrate_cathode,
            realrate_anode,
        )

    if not json_data:
        logger.warning("No valid data found in %s", target_filepath)
        return False

    logger.info(
        "Processing file%s: %s - %d valid line(s)",
        (f" ({index}/{total})" if index is not None else ""),
        target_filepath,
        valid_lines,
    )
    logger.info("Sending %d record(s) from %s to InfluxDB", len(json_data), target_filepath)

    # Send with retry on exception or write failure
    backoff = INITIAL_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = client.write_points(json_data)
            if result:
                logger.info("Wrote %s (%d/%d) to InfluxDB", target_filepath, attempt, MAX_RETRIES)
                return True
            else:
                logger.warning("Influx write returned False on attempt %d for %s", attempt, target_filepath)
        except Exception as e:
            logger.exception("Influx write failed on attempt %d for %s: %s", attempt, target_filepath, e)

        if attempt < MAX_RETRIES:
            logger.info("Retrying in %s seconds... (attempt %d/%d)", backoff, attempt + 1, MAX_RETRIES)
            time.sleep(backoff)
            backoff *= 2
        else:
            logger.error("Exceeded max retries (%d) for writing to InfluxDB for %s", MAX_RETRIES, target_filepath)
            return False


def main():
    path = Path(RATEPATH)
    if not path.exists():
        logger.error("Configured rate path does not exist: %s", path)
        return

    logger.info("Starting periodic polling every %s seconds (mode=%s) on %s", INTERVAL_SECONDS, MODE, path)
    try:
        if MODE == "all":
            files = sorted([p for p in path.iterdir() if p.is_file()], key=lambda p: p.stat().st_mtime)
            total = len(files)
            logger.info("Found %d file(s) to process", total)
            for idx, p in enumerate(files, start=1):
                logger.info("Processing file %d/%d: %s", idx, total, p)
                try:
                    success = process_file(str(p), index=idx, total=total)
                    if not success:
                        logger.warning("Processing failed for %s", p)
                except Exception:
                    logger.exception("Unhandled error processing %s", p)
            logger.info("All mode completed; exiting after one pass")
            return

        while True:
            files = [p for p in path.iterdir() if p.is_file()]
            if not files:
                logger.debug("No files found in %s", path)
            else:
                latest = max(files, key=lambda p: p.stat().st_mtime)
                logger.info("Processing latest file: %s", latest)
                try:
                    success = process_file(str(latest), index=1, total=1)
                    if not success:
                        logger.warning("Processing failed for %s", latest)
                except Exception:
                    logger.exception("Unhandled error processing %s", latest)

            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Interrupted, exiting")


if __name__ == "__main__":
    main()
