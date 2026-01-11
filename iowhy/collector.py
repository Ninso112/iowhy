"""
I/O statistics collector module.

Collects process and device I/O statistics from /proc and /sys filesystems.
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ProcessIOStats:
    """I/O statistics for a single process."""

    def __init__(self, pid: int, name: str = "", command: str = ""):
        self.pid = pid
        self.name = name
        self.command = command
        self.rchar = 0
        self.wchar = 0
        self.read_bytes = 0
        self.write_bytes = 0
        self.syscr = 0
        self.syscw = 0

    def __repr__(self):
        return (
            f"ProcessIOStats(pid={self.pid}, name={self.name}, "
            f"read_bytes={self.read_bytes}, write_bytes={self.write_bytes})"
        )


class DeviceIOStats:
    """I/O statistics for a single device."""

    def __init__(self, name: str):
        self.name = name
        self.major = 0
        self.minor = 0
        self.reads = 0
        self.read_merges = 0
        self.read_sectors = 0
        self.read_time_ms = 0
        self.writes = 0
        self.write_merges = 0
        self.write_sectors = 0
        self.write_time_ms = 0
        self.io_in_progress = 0
        self.io_time_ms = 0
        self.weighted_io_time_ms = 0

    def __repr__(self):
        return (
            f"DeviceIOStats(name={self.name}, reads={self.reads}, "
            f"writes={self.writes}, read_sectors={self.read_sectors}, "
            f"write_sectors={self.write_sectors})"
        )


def collect_process_io(pid: int) -> Optional[ProcessIOStats]:
    """
    Collect I/O statistics for a single process.

    Args:
        pid: Process ID

    Returns:
        ProcessIOStats object or None if stats cannot be read
    """
    proc_path = Path(f"/proc/{pid}")

    if not proc_path.exists():
        return None

    try:
        # Read process name from comm
        comm_path = proc_path / "comm"
        name = comm_path.read_text().strip() if comm_path.exists() else ""

        # Read command line (for more context)
        cmdline_path = proc_path / "cmdline"
        command = ""
        if cmdline_path.exists():
            try:
                cmdline = cmdline_path.read_text().strip("\x00")
                # Take first part of command line, limit length
                parts = cmdline.split("\x00")
                command = parts[0] if parts else ""
                if len(command) > 60:
                    command = command[:57] + "..."
            except (OSError, IOError):
                pass

        # Read I/O statistics
        io_path = proc_path / "io"
        if not io_path.exists():
            return None

        try:
            io_data = io_path.read_text()
        except (OSError, IOError, PermissionError):
            # Cannot read /proc/[pid]/io without sufficient permissions
            return None

        stats = ProcessIOStats(pid, name, command)

        # Parse /proc/[pid]/io format
        for line in io_data.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                try:
                    val = int(value)
                    if key == "rchar":
                        stats.rchar = val
                    elif key == "wchar":
                        stats.wchar = val
                    elif key == "read_bytes":
                        stats.read_bytes = val
                    elif key == "write_bytes":
                        stats.write_bytes = val
                    elif key == "syscr":
                        stats.syscr = val
                    elif key == "syscw":
                        stats.syscw = val
                except ValueError:
                    continue

        return stats

    except (OSError, IOError, PermissionError):
        return None


def collect_all_process_io() -> List[ProcessIOStats]:
    """
    Collect I/O statistics for all processes.

    Returns:
        List of ProcessIOStats objects
    """
    processes = []
    proc_path = Path("/proc")

    if not proc_path.exists():
        return processes

    try:
        # Scan /proc for numeric PIDs
        for entry in proc_path.iterdir():
            if not entry.is_dir():
                continue

            try:
                pid = int(entry.name)
            except ValueError:
                continue

            stats = collect_process_io(pid)
            if stats is not None:
                processes.append(stats)

    except (OSError, IOError, PermissionError):
        pass

    return processes


def collect_device_io() -> Dict[str, DeviceIOStats]:
    """
    Collect I/O statistics for all devices from /proc/diskstats.

    Returns:
        Dictionary mapping device names to DeviceIOStats objects
    """
    devices = {}
    diskstats_path = Path("/proc/diskstats")

    if not diskstats_path.exists():
        return devices

    try:
        diskstats_data = diskstats_path.read_text()
    except (OSError, IOError, PermissionError):
        return devices

    # Parse /proc/diskstats format
    # Format: major minor name rio rmerge rsect ruse wio wmerge wsect wuse running use aveq
    for line in diskstats_data.splitlines():
        if not line.strip():
            continue

        parts = line.split()
        if len(parts) < 14:
            continue

        try:
            major = int(parts[0])
            minor = int(parts[1])
            name = parts[2]

            # Filter out loop devices and partitions if desired
            # (Keep them for now, user can filter in display)

            stats = DeviceIOStats(name)
            stats.major = major
            stats.minor = minor
            stats.reads = int(parts[3])
            stats.read_merges = int(parts[4])
            stats.read_sectors = int(parts[5])
            stats.read_time_ms = int(parts[6])
            stats.writes = int(parts[7])
            stats.write_merges = int(parts[8])
            stats.write_sectors = int(parts[9])
            stats.write_time_ms = int(parts[10])
            stats.io_in_progress = int(parts[11])
            stats.io_time_ms = int(parts[12])
            stats.weighted_io_time_ms = int(parts[13])

            devices[name] = stats

        except (ValueError, IndexError):
            continue

    return devices


def calculate_io_deltas(
    before: List[ProcessIOStats], after: List[ProcessIOStats]
) -> List[ProcessIOStats]:
    """
    Calculate I/O deltas between two snapshots (for sampling).

    Args:
        before: First snapshot of process stats
        after: Second snapshot of process stats

    Returns:
        List of ProcessIOStats with delta values
    """
    # Create lookup by PID
    before_dict = {p.pid: p for p in before}
    deltas = []

    for after_stat in after:
        pid = after_stat.pid
        before_stat = before_dict.get(pid)

        if before_stat is None:
            # Process started during sampling, use current values
            delta = ProcessIOStats(pid, after_stat.name, after_stat.command)
            delta.rchar = after_stat.rchar
            delta.wchar = after_stat.wchar
            delta.read_bytes = after_stat.read_bytes
            delta.write_bytes = after_stat.write_bytes
            delta.syscr = after_stat.syscr
            delta.syscw = after_stat.syscw
        else:
            # Calculate delta
            delta = ProcessIOStats(pid, after_stat.name, after_stat.command)
            delta.rchar = max(0, after_stat.rchar - before_stat.rchar)
            delta.wchar = max(0, after_stat.wchar - before_stat.wchar)
            delta.read_bytes = max(0, after_stat.read_bytes - before_stat.read_bytes)
            delta.write_bytes = max(0, after_stat.write_bytes - before_stat.write_bytes)
            delta.syscr = max(0, after_stat.syscr - before_stat.syscr)
            delta.syscw = max(0, after_stat.syscw - before_stat.syscw)

        deltas.append(delta)

    return deltas


def calculate_device_io_deltas(
    before: Dict[str, DeviceIOStats], after: Dict[str, DeviceIOStats]
) -> Dict[str, DeviceIOStats]:
    """
    Calculate I/O deltas for devices between two snapshots.

    Args:
        before: First snapshot of device stats
        after: Second snapshot of device stats

    Returns:
        Dictionary of DeviceIOStats with delta values
    """
    deltas = {}

    for name, after_stat in after.items():
        before_stat = before.get(name)

        if before_stat is None:
            # Device appeared during sampling
            delta = DeviceIOStats(name)
            delta.major = after_stat.major
            delta.minor = after_stat.minor
            delta.reads = after_stat.reads
            delta.writes = after_stat.writes
            delta.read_sectors = after_stat.read_sectors
            delta.write_sectors = after_stat.write_sectors
            # Copy other fields
            delta.read_merges = after_stat.read_merges
            delta.read_time_ms = after_stat.read_time_ms
            delta.write_merges = after_stat.write_merges
            delta.write_time_ms = after_stat.write_time_ms
            delta.io_in_progress = after_stat.io_in_progress
            delta.io_time_ms = after_stat.io_time_ms
            delta.weighted_io_time_ms = after_stat.weighted_io_time_ms
        else:
            # Calculate delta
            delta = DeviceIOStats(name)
            delta.major = after_stat.major
            delta.minor = after_stat.minor
            delta.reads = max(0, after_stat.reads - before_stat.reads)
            delta.writes = max(0, after_stat.writes - before_stat.writes)
            delta.read_sectors = max(0, after_stat.read_sectors - before_stat.read_sectors)
            delta.write_sectors = max(0, after_stat.write_sectors - before_stat.write_sectors)
            delta.read_merges = max(0, after_stat.read_merges - before_stat.read_merges)
            delta.read_time_ms = max(0, after_stat.read_time_ms - before_stat.read_time_ms)
            delta.write_merges = max(0, after_stat.write_merges - before_stat.write_merges)
            delta.write_time_ms = max(0, after_stat.write_time_ms - before_stat.write_time_ms)
            delta.io_in_progress = after_stat.io_in_progress  # Current value, not delta
            delta.io_time_ms = max(0, after_stat.io_time_ms - before_stat.io_time_ms)
            delta.weighted_io_time_ms = max(
                0, after_stat.weighted_io_time_ms - before_stat.weighted_io_time_ms
            )

        deltas[name] = delta

    return deltas


def sample_io(duration: float) -> Tuple[List[ProcessIOStats], Dict[str, DeviceIOStats]]:
    """
    Sample I/O statistics over a time period.

    Args:
        duration: Sampling duration in seconds

    Returns:
        Tuple of (process_deltas, device_deltas)
    """
    # Take initial snapshot
    before_processes = collect_all_process_io()
    before_devices = collect_device_io()

    # Wait
    time.sleep(duration)

    # Take second snapshot
    after_processes = collect_all_process_io()
    after_devices = collect_device_io()

    # Calculate deltas
    process_deltas = calculate_io_deltas(before_processes, after_processes)
    device_deltas = calculate_device_io_deltas(before_devices, after_devices)

    return process_deltas, device_deltas
