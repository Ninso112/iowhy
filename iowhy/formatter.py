"""
Output formatting module.

Handles both human-readable text output and JSON output.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

from .collector import DeviceIOStats, ProcessIOStats


# ANSI color codes
COLOR_RESET = "\033[0m"
COLOR_GREEN = "\033[1;32m"
COLOR_RED = "\033[1;31m"
COLOR_YELLOW = "\033[1;33m"
COLOR_BLUE = "\033[1;34m"
COLOR_CYAN = "\033[1;36m"


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes into human-readable format.

    Args:
        bytes_value: Number of bytes

    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.1f} KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024):.1f} MB"
    elif bytes_value < 1024 * 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024 * 1024):.1f} GB"
    else:
        return f"{bytes_value / (1024 * 1024 * 1024 * 1024):.1f} TB"


def format_bytes_with_raw(bytes_value: int) -> str:
    """
    Format bytes with both human-readable and raw values.

    Args:
        bytes_value: Number of bytes

    Returns:
        Formatted string (e.g., "1.5 GB (1610612736)")
    """
    formatted = format_bytes(bytes_value)
    return f"{formatted} ({bytes_value})"


def sort_processes_by_io(processes: List[ProcessIOStats]) -> List[ProcessIOStats]:
    """
    Sort processes by total I/O activity (read_bytes + write_bytes).

    Args:
        processes: List of ProcessIOStats

    Returns:
        Sorted list (highest I/O first)
    """
    return sorted(
        processes, key=lambda p: p.read_bytes + p.write_bytes, reverse=True
    )


def generate_summary(
    top_processes: List[ProcessIOStats],
    devices: Dict[str, DeviceIOStats],
    duration: Optional[float] = None,
) -> str:
    """
    Generate a human-readable summary/diagnosis.

    Args:
        top_processes: Top processes by I/O
        devices: Device statistics
        duration: Sampling duration in seconds (if sampling was used)

    Returns:
        Summary text
    """
    if not top_processes:
        return "No I/O activity detected or insufficient permissions to read process statistics."

    lines = []

    # Analyze top process
    top = top_processes[0]
    total_io = top.read_bytes + top.write_bytes

    if duration:
        rate = total_io / duration if duration > 0 else 0
        rate_str = format_bytes(int(rate))
        lines.append(
            f"Highest I/O activity: Process '{top.name}' (PID {top.pid}) "
            f"with {rate_str}/s ({format_bytes_with_raw(total_io)} in {duration:.1f}s)"
        )
    else:
        lines.append(
            f"Highest I/O activity: Process '{top.name}' (PID {top.pid}) "
            f"with {format_bytes_with_raw(total_io)} total"
        )

    # Check if multiple processes are involved
    if len(top_processes) > 1:
        second = top_processes[1]
        second_io = second.read_bytes + second.write_bytes
        if second_io > total_io * 0.1:  # More than 10% of top process
            lines.append(
                f"Secondary contributor: Process '{second.name}' (PID {second.pid}) "
                f"with {format_bytes_with_raw(second_io)}"
            )

    # Analyze device activity if available
    if devices:
        # Find device with most activity
        device_list = list(devices.values())
        device_list.sort(
            key=lambda d: d.read_sectors + d.write_sectors, reverse=True
        )

        if device_list:
            top_device = device_list[0]
            total_sectors = top_device.read_sectors + top_device.write_sectors
            # Assume 512 bytes per sector
            total_bytes = total_sectors * 512

            if duration and duration > 0:
                rate = total_bytes / duration
                rate_str = format_bytes(int(rate))
                lines.append(
                    f"Most active device: {top_device.name} "
                    f"({rate_str}/s, {format_bytes_with_raw(total_bytes)} in {duration:.1f}s)"
                )
            else:
                lines.append(
                    f"Most active device: {top_device.name} "
                    f"({format_bytes_with_raw(total_bytes)} total)"
                )

            # Link process to device if possible
            lines.append(
                f"I/O seems concentrated on /dev/{top_device.name} by process '{top.name}'"
            )

    return "\n".join(lines)


def format_text_output(
    processes: List[ProcessIOStats],
    devices: Optional[Dict[str, DeviceIOStats]] = None,
    top_n: int = 5,
    duration: Optional[float] = None,
    use_color: bool = True,
) -> str:
    """
    Format output as human-readable text.

    Args:
        processes: List of process I/O statistics
        devices: Optional device statistics dictionary
        top_n: Number of top processes to show
        duration: Sampling duration in seconds (if sampling was used)
        use_color: Whether to use ANSI color codes

    Returns:
        Formatted text string
    """
    output_lines = []

    # Header
    if use_color:
        output_lines.append(f"{COLOR_CYAN}=== I/O Activity Analysis ==={COLOR_RESET}")
    else:
        output_lines.append("=== I/O Activity Analysis ===")

    if duration:
        output_lines.append(f"Sampling duration: {duration:.1f} seconds")
        output_lines.append("(Values shown are rates during sampling period)")
    else:
        output_lines.append("(Values shown are cumulative since process start)")

    output_lines.append("")

    # Sort processes
    sorted_processes = sort_processes_by_io(processes)
    top_processes = sorted_processes[:top_n]

    if not top_processes:
        output_lines.append("No process I/O statistics available.")
        return "\n".join(output_lines)

    # Process table header
    output_lines.append(f"Top {len(top_processes)} processes by I/O:")
    output_lines.append("")

    if use_color:
        header = (
            f"{COLOR_BLUE}{'PID':<8} {'Process':<20} {'Read':<25} "
            f"{'Write':<25} {'Read Ops':<12} {'Write Ops':<12}{COLOR_RESET}"
        )
    else:
        header = (
            f"{'PID':<8} {'Process':<20} {'Read':<25} "
            f"{'Write':<25} {'Read Ops':<12} {'Write Ops':<12}"
        )
    output_lines.append(header)
    output_lines.append("-" * len(header))

    # Process rows
    for proc in top_processes:
        read_str = format_bytes_with_raw(proc.read_bytes)
        write_str = format_bytes_with_raw(proc.write_bytes)

        process_name = proc.name[:18] if len(proc.name) <= 18 else proc.name[:15] + "..."

        if use_color:
            line = (
                f"{COLOR_GREEN}{proc.pid:<8}{COLOR_RESET} "
                f"{process_name:<20} {read_str:<25} {write_str:<25} "
                f"{proc.syscr:<12} {proc.syscw:<12}"
            )
        else:
            line = (
                f"{proc.pid:<8} {process_name:<20} {read_str:<25} {write_str:<25} "
                f"{proc.syscr:<12} {proc.syscw:<12}"
            )
        output_lines.append(line)

    output_lines.append("")

    # Device statistics (if requested)
    if devices:
        output_lines.append("Device I/O Statistics:")
        output_lines.append("")

        device_list = list(devices.values())
        device_list.sort(
            key=lambda d: d.read_sectors + d.write_sectors, reverse=True
        )

        # Show top 10 devices
        top_devices = device_list[:10]

        if use_color:
            dev_header = (
                f"{COLOR_BLUE}{'Device':<15} {'Reads':<12} {'Writes':<12} "
                f"{'Read Sectors':<15} {'Write Sectors':<15}{COLOR_RESET}"
            )
        else:
            dev_header = (
                f"{'Device':<15} {'Reads':<12} {'Writes':<12} "
                f"{'Read Sectors':<15} {'Write Sectors':<15}"
            )
        output_lines.append(dev_header)
        output_lines.append("-" * len(dev_header))

        for dev in top_devices:
            read_bytes = dev.read_sectors * 512
            write_bytes = dev.write_sectors * 512

            if duration and duration > 0:
                reads_per_sec = dev.reads / duration if duration > 0 else 0
                writes_per_sec = dev.writes / duration if duration > 0 else 0
                read_bytes_per_sec = read_bytes / duration if duration > 0 else 0
                write_bytes_per_sec = write_bytes / duration if duration > 0 else 0
                reads_str = f"{reads_per_sec:.1f}/s"
                writes_str = f"{writes_per_sec:.1f}/s"
                read_sectors_str = format_bytes(int(read_bytes_per_sec)) + "/s"
                write_sectors_str = format_bytes(int(write_bytes_per_sec)) + "/s"
            else:
                reads_str = str(dev.reads)
                writes_str = str(dev.writes)
                read_sectors_str = format_bytes(read_bytes)
                write_sectors_str = format_bytes(write_bytes)

            if use_color:
                line = (
                    f"{COLOR_CYAN}{dev.name:<15}{COLOR_RESET} {reads_str:<12} "
                    f"{writes_str:<12} {read_sectors_str:<15} {write_sectors_str:<15}"
                )
            else:
                line = (
                    f"{dev.name:<15} {reads_str:<12} {writes_str:<12} "
                    f"{read_sectors_str:<15} {write_sectors_str:<15}"
                )
            output_lines.append(line)

        output_lines.append("")

    # Summary
    summary = generate_summary(top_processes, devices or {}, duration)
    output_lines.append("Summary:")
    output_lines.append("")
    if use_color:
        output_lines.append(f"{COLOR_YELLOW}{summary}{COLOR_RESET}")
    else:
        output_lines.append(summary)

    return "\n".join(output_lines)


def format_json_output(
    processes: List[ProcessIOStats],
    devices: Optional[Dict[str, DeviceIOStats]] = None,
    top_n: int = 5,
    duration: Optional[float] = None,
) -> str:
    """
    Format output as JSON.

    Args:
        processes: List of process I/O statistics
        devices: Optional device statistics dictionary
        top_n: Number of top processes to include
        duration: Sampling duration in seconds (if sampling was used)

    Returns:
        JSON string
    """
    # Sort processes
    sorted_processes = sort_processes_by_io(processes)
    top_processes = sorted_processes[:top_n]

    # Build JSON structure
    result = {
        "timestamp": datetime.now().isoformat(),
        "sampling_duration_seconds": duration,
        "top_processes": [],
        "summary": generate_summary(top_processes, devices or {}, duration),
    }

    # Add process data
    for proc in top_processes:
        result["top_processes"].append(
            {
                "pid": proc.pid,
                "name": proc.name,
                "command": proc.command,
                "read_bytes": proc.read_bytes,
                "write_bytes": proc.write_bytes,
                "read_bytes_formatted": format_bytes(proc.read_bytes),
                "write_bytes_formatted": format_bytes(proc.write_bytes),
                "read_operations": proc.syscr,
                "write_operations": proc.syscw,
                "total_io_bytes": proc.read_bytes + proc.write_bytes,
            }
        )

    # Add device data if requested
    if devices:
        result["devices"] = []
        device_list = list(devices.values())
        device_list.sort(
            key=lambda d: d.read_sectors + d.write_sectors, reverse=True
        )

        for dev in device_list[:10]:  # Top 10 devices
            read_bytes = dev.read_sectors * 512
            write_bytes = dev.write_sectors * 512

            dev_data = {
                "name": dev.name,
                "major": dev.major,
                "minor": dev.minor,
                "reads": dev.reads,
                "writes": dev.writes,
                "read_sectors": dev.read_sectors,
                "write_sectors": dev.write_sectors,
                "read_bytes": read_bytes,
                "write_bytes": write_bytes,
                "read_bytes_formatted": format_bytes(read_bytes),
                "write_bytes_formatted": format_bytes(write_bytes),
            }

            if duration and duration > 0:
                dev_data["reads_per_second"] = dev.reads / duration
                dev_data["writes_per_second"] = dev.writes / duration
                dev_data["read_bytes_per_second"] = read_bytes / duration
                dev_data["write_bytes_per_second"] = write_bytes / duration

            result["devices"].append(dev_data)

    return json.dumps(result, indent=2)
