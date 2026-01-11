# iowhy

iowhy is a lightweight Linux command-line tool that identifies disk I/O bottlenecks. It inspects per-process and per-device I/O statistics, highlights the top readers/writers, and summarizes whether your system is blocked by heavy disk activity.

## Features

- **Process I/O Analysis**: Identifies which processes are responsible for the most disk I/O
- **Device Statistics**: Optional breakdown of I/O activity by device (e.g., `/dev/nvme0n1`)
- **Sampling Mode**: Measures current I/O activity over a configurable time window
- **Flexible Output**: Human-readable text output with optional colors, or structured JSON
- **Lightweight**: Uses only Python standard library, no external dependencies

## Installation

### From Source

```bash
git clone <repository-url>
cd iowhy
pip install .
```

After installation, the `iowhy` command will be available in your PATH.

## Usage

### Quick Diagnosis

Run iowhy without arguments for a quick 2-second analysis:

```bash
iowhy
```

This will show the top 5 processes by I/O activity and a summary of what's causing disk I/O load.

### Extended Monitoring

Sample I/O activity over a longer period:

```bash
iowhy --duration 10
```

### Show More Processes

Display the top 10 processes:

```bash
iowhy --top 10
```

### Per-Device Breakdown

Include device-level I/O statistics:

```bash
iowhy --by-device
```

### JSON Output

Get structured output for scripting:

```bash
iowhy --json
```

### Combining Options

Combine multiple options:

```bash
iowhy --duration 5 --top 10 --by-device --json
```

Disable colored output:

```bash
iowhy --no-color
```

## Command-Line Options

- `--top N`: Number of top processes to show (default: 5)
- `--duration SECONDS`: Sampling duration in seconds (default: 2.0)
- `--by-device`: Include device I/O statistics breakdown
- `--json`: Output results in JSON format
- `--no-color`: Disable colored output

## Output Format

### Text Output

The default text output shows:

1. **Header**: Sampling information and interpretation guide
2. **Top Processes Table**: 
   - PID, process name
   - Read/write bytes (formatted and raw)
   - Read/write operation counts
3. **Device Statistics** (if `--by-device` is used):
   - Device name
   - Read/write counts and rates
   - Sector counts
4. **Summary**: Human-readable diagnosis identifying the main I/O contributors

### JSON Output

When using `--json`, the output is a structured JSON object containing:

- `timestamp`: ISO timestamp of the analysis
- `sampling_duration_seconds`: Duration used for sampling
- `top_processes`: Array of process objects with I/O statistics
- `devices`: Array of device objects (if `--by-device` is used)
- `summary`: Text summary of findings

## Examples

### Example 1: Quick Check

```bash
$ iowhy
=== I/O Activity Analysis ===
Sampling duration: 2.0 seconds
(Values shown are rates during sampling period)

Top 5 processes by I/O:

PID      Process              Read                      Write                     Read Ops    Write Ops  
----------------------------------------------------------------------------------------------------------
1234     python3              1.2 GB (1342177280)      250.5 MB (262144000)      1024        512        
5678     postgres             500.0 MB (524288000)     1.0 GB (1073741824)       2048        1024       

Summary:
Highest I/O activity: Process 'python3' (PID 1234) with 600.0 MB/s (1.5 GB (1604321280) in 2.0s)
Most active device: nvme0n1 (750.0 MB/s, 1.5 GB (1572864000) in 2.0s)
I/O seems concentrated on /dev/nvme0n1 by process 'python3'
```

### Example 2: JSON Output

```bash
$ iowhy --json --top 3
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "sampling_duration_seconds": 2.0,
  "top_processes": [
    {
      "pid": 1234,
      "name": "python3",
      "read_bytes": 1342177280,
      "write_bytes": 262144000,
      "read_bytes_formatted": "1.2 GB",
      "write_bytes_formatted": "250.5 MB",
      "read_operations": 1024,
      "write_operations": 512,
      "total_io_bytes": 1604321280
    }
  ],
  "summary": "..."
}
```

## Limitations

- **Linux-only**: This tool requires Linux and the `/proc` filesystem
- **Permissions**: Some I/O statistics (from `/proc/[pid]/io`) may require root privileges to read for processes owned by other users
- **Process Visibility**: Only processes accessible to the current user will be shown
- **Sampling Accuracy**: Short sampling durations may miss brief I/O bursts

## How It Works

iowhy collects I/O statistics from:

- `/proc/[pid]/io`: Per-process I/O statistics (reads, writes, bytes)
- `/proc/diskstats`: Device-level I/O statistics (sectors, operations)

When sampling mode is used (default), iowhy:

1. Takes an initial snapshot of all process and device statistics
2. Waits for the specified duration
3. Takes a second snapshot
4. Calculates the differences (deltas) to show current I/O rates

When sampling is disabled (duration = 0), cumulative statistics since process start are shown.

## License

This project is licensed under the GNU General Public License v3 (GPLv3). See the [LICENSE](LICENSE) file for details.
