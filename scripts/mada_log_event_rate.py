#! /usr/bin/env python3

"""Event-rate logger that reads files under a directory and writes to InfluxDB."""

import os
import time
import json
import logging
import datetime
from pathlib import Path

from influxdb import InfluxDBClient


# Load configuration.
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "MADA_logEventRate.json"
config_path = os.environ.get("MADA_LOGEVENTRATE_CONFIG", str(DEFAULT_CONFIG))
with open(config_path, "r") as cf:
    cfg = json.load(cf)


# Normalize directory path.
EVENTRATE_PATH = os.path.expanduser(cfg.get("eventrate_path", "."))


# Setup InfluxDB client from config.
influx_cfg = cfg.get("influx", {})
client = InfluxDBClient(
    host=influx_cfg.get("host", "localhost"),
    port=int(influx_cfg.get("port", 8086)),
    username=influx_cfg.get("username"),
    password=influx_cfg.get("password"),
    database=influx_cfg.get("database"),
)


TAGS = cfg.get("tags", {})
RETRY_CFG = cfg.get("retry", {})
MAX_RETRIES = int(RETRY_CFG.get("max_retries", 3))
INITIAL_BACKOFF = float(RETRY_CFG.get("initial_backoff", 1.0))
INTERVAL_SECONDS = int(cfg.get("interval_seconds", 10))
MODE = cfg.get("mode", "latest").lower()
MEASUREMENT = cfg.get("measurement", "rate")


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MADA_logEventRate")


def process_file(target_filepath, index=None, total=None):
    """Read every valid line in a file and send all records to InfluxDB."""
    try:
        with open(target_filepath, "r") as f:
            lines = f.readlines()
    except Exception as e:
        logger.exception("Failed to read file %s: %s", target_filepath, e)
        return False

    if not lines:
        logger.warning("File is empty: %s", target_filepath)
        return False

    json_data = []
    valid_lines = 0
    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 5:
            logger.warning("Unexpected line format in %s line %d: %s", target_filepath, line_no, line)
            continue

        try:
            realtime_clk = float(parts[1])
            livetime_clk = float(parts[2])
            num_trigger = float(parts[3])
            unixtime = float(parts[4])
        except Exception:
            logger.exception("Failed to parse numeric fields from %s line %d: %s", target_filepath, line_no, line)
            continue

        if realtime_clk < 1 or livetime_clk < 1:
            logger.info("realtime or livetime is zero at %s line %d; skipping", target_filepath, line_no)
            continue

        realtime = realtime_clk * 1e-4
        livetime = livetime_clk * 1e-4
        trigger_rate_real = num_trigger / realtime
        trigger_rate_live = num_trigger / livetime
        scalertime = datetime.datetime.utcfromtimestamp(unixtime)

        json_data.append(
            {
                "measurement": MEASUREMENT,
                "fields": {
                    "trigger_rate_real": trigger_rate_real,
                    "trigger_rate_live": trigger_rate_live,
                },
                "time": scalertime.isoformat() + "Z",
                "tags": TAGS,
            }
        )
        valid_lines += 1
        logger.info(
            "Parsed line %d/%d from %s: real=%s, live=%s",
            line_no,
            len(lines),
            target_filepath,
            trigger_rate_real,
            trigger_rate_live,
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

    backoff = INITIAL_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = client.write_points(json_data)
            if result:
                logger.info("Wrote %s (%d/%d) to InfluxDB", target_filepath, attempt, MAX_RETRIES)
                return True
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


def collect_files(path):
    """Collect files recursively under the configured directory."""
    return sorted([p for p in path.rglob("*") if p.is_file()], key=lambda p: p.stat().st_mtime)


def main():
    path = Path(EVENTRATE_PATH)
    if not path.exists():
        logger.error("Configured event-rate path does not exist: %s", path)
        return

    logger.info("Starting periodic polling every %s seconds (mode=%s) on %s", INTERVAL_SECONDS, MODE, path)
    try:
        if MODE == "all":
            files = collect_files(path)
            total = len(files)
            logger.info("Found %d file(s) to process", total)
            for idx, file_path in enumerate(files, start=1):
                logger.info("Processing file %d/%d: %s", idx, total, file_path)
                try:
                    success = process_file(str(file_path), index=idx, total=total)
                    if not success:
                        logger.warning("Processing failed for %s", file_path)
                except Exception:
                    logger.exception("Unhandled error processing %s", file_path)
            logger.info("All mode completed; exiting after one pass")
            return

        while True:
            files = collect_files(path)
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


