"""
Command-line interface for iowhy.
"""

import argparse
import sys

from .collector import collect_all_process_io, collect_device_io, sample_io
from .formatter import format_json_output, format_text_output


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Identify disk I/O bottlenecks on Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Quick diagnosis with 2-second sampling
  %(prog)s --duration 5       # Sample for 5 seconds
  %(prog)s --top 10           # Show top 10 processes
  %(prog)s --by-device        # Include device breakdown
  %(prog)s --json             # Output as JSON
  %(prog)s --no-color         # Disable colored output
        """,
    )

    parser.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="N",
        help="Number of top processes to show (default: 5)",
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=2.0,
        metavar="SECONDS",
        help="Sampling duration in seconds (default: 2.0)",
    )

    parser.add_argument(
        "--by-device",
        action="store_true",
        help="Include device I/O statistics breakdown",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    return parser.parse_args()


def main():
    """Main entry point for the CLI."""
    args = parse_arguments()

    # Validate arguments
    if args.top < 1:
        print("Error: --top must be at least 1", file=sys.stderr)
        sys.exit(1)

    if args.duration < 0:
        print("Error: --duration must be non-negative", file=sys.stderr)
        sys.exit(1)

    try:
        # Sample I/O statistics
        if args.duration > 0:
            try:
                processes, devices = sample_io(args.duration)
            except KeyboardInterrupt:
                print("\nInterrupted by user", file=sys.stderr)
                sys.exit(130)
            except Exception as e:
                print(f"Error during sampling: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # No sampling, just collect current stats
            processes = collect_all_process_io()
            devices = collect_device_io() if args.by_device else {}

        # Filter devices if not requested
        if not args.by_device:
            devices = {}

        # Format and output
        if args.json:
            output = format_json_output(
                processes, devices, top_n=args.top, duration=args.duration if args.duration > 0 else None
            )
        else:
            output = format_text_output(
                processes,
                devices,
                top_n=args.top,
                duration=args.duration if args.duration > 0 else None,
                use_color=not args.no_color,
            )

        print(output)

    except PermissionError as e:
        print(
            f"Permission denied: {e}\n"
            "Note: Some I/O statistics may require root privileges to read.",
            file=sys.stderr,
        )
        sys.exit(1)
    except FileNotFoundError as e:
        print(
            f"Required file not found: {e}\n"
            "This tool requires Linux with /proc filesystem.",
            file=sys.stderr,
        )
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
