#!/usr/bin/env python3
"""
Real tap simulation using sendevent to bypass anti-bot detection.

This script simulates realistic touch events that are harder for apps like
DingTalk (钉钉) to detect as automated taps.

For rooted devices: Uses sendevent for low-level touch events.
For non-rooted devices: Uses input swipe with timing variations.
"""

import argparse
import random
import subprocess
import sys
import time


def get_adb_prefix(device_id: str | None = None) -> list[str]:
    """Get ADB command prefix."""
    if device_id:
        return ["adb", "-s", device_id]
    return ["adb"]


def run_adb(cmd: list[str], device_id: str | None = None) -> str:
    """Run an ADB command and return output."""
    prefix = get_adb_prefix(device_id)
    result = subprocess.run(prefix + cmd, capture_output=True, text=True)
    return result.stdout


def run_adb_with_code(cmd: list[str], device_id: str | None = None) -> tuple[str, str, int]:
    """Run an ADB command and return output, stderr, and return code."""
    prefix = get_adb_prefix(device_id)
    result = subprocess.run(prefix + cmd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


def is_device_rooted(device_id: str | None = None) -> bool:
    """Check if device has root access."""
    # Try running a simple command with su
    stdout, stderr, code = run_adb_with_code(["shell", "su", "-c", "id"], device_id)
    return code == 0 and "uid=0" in stdout


def get_touch_device(device_id: str | None = None) -> str | None:
    """Find the touch input device path."""
    output = run_adb(["shell", "getevent", "-pl"], device_id)

    current_device = None
    for line in output.split("\n"):
        if line.startswith("add device"):
            # Extract device path like /dev/input/event2
            parts = line.split(":")
            if len(parts) >= 2:
                current_device = parts[1].strip()
        elif "ABS_MT_POSITION_X" in line and current_device:
            return current_device

    return None


def get_screen_resolution(device_id: str | None = None) -> tuple[int, int]:
    """Get device screen resolution."""
    output = run_adb(["shell", "wm", "size"], device_id)
    # Output format: "Physical size: 1080x2400"
    for line in output.split("\n"):
        if "size" in line.lower():
            parts = line.split(":")
            if len(parts) >= 2:
                size = parts[1].strip()
                w, h = size.split("x")
                return int(w), int(h)
    return 1080, 2400  # Default fallback


def get_touch_range(device_id: str | None = None, device_path: str | None = None) -> dict:
    """Get touch device coordinate ranges."""
    output = run_adb(["shell", "getevent", "-pl"], device_id)

    ranges = {
        "x_min": 0,
        "x_max": 32767,
        "y_min": 0,
        "y_max": 32767,
        "pressure_max": 255,
        "touch_major_max": 255,
    }

    in_target_device = False
    for line in output.split("\n"):
        if line.startswith("add device") and device_path and device_path in line:
            in_target_device = True
        elif line.startswith("add device") and in_target_device:
            break
        elif in_target_device:
            if "ABS_MT_POSITION_X" in line:
                # Parse: "value 0, min 0, max 1079, fuzz 0, flat 0, resolution 0"
                if "max" in line:
                    parts = line.split(",")
                    for part in parts:
                        if "max" in part:
                            ranges["x_max"] = int(part.split()[-1])
            elif "ABS_MT_POSITION_Y" in line:
                if "max" in line:
                    parts = line.split(",")
                    for part in parts:
                        if "max" in part:
                            ranges["y_max"] = int(part.split()[-1])
            elif "ABS_MT_PRESSURE" in line:
                if "max" in line:
                    parts = line.split(",")
                    for part in parts:
                        if "max" in part:
                            ranges["pressure_max"] = int(part.split()[-1])
            elif "ABS_MT_TOUCH_MAJOR" in line:
                if "max" in line:
                    parts = line.split(",")
                    for part in parts:
                        if "max" in part:
                            ranges["touch_major_max"] = int(part.split()[-1])

    return ranges


def sendevent(device_id: str | None, device_path: str, event_type: int, code: int, value: int):
    """Send a single event."""
    cmd = ["shell", "sendevent", device_path, str(event_type), str(code), str(value)]
    run_adb(cmd, device_id)


def real_tap_swipe(
    x: int,
    y: int,
    device_id: str | None = None,
    verbose: bool = False,
    humanize: bool = True,
) -> bool:
    """
    Simulate a realistic tap using input swipe (for non-rooted devices).

    Uses a very short swipe with human-like timing to simulate a tap.
    This method is harder to detect than simple 'input tap'.
    """
    # Add human-like variations
    if humanize:
        # Small random offset (±3 pixels)
        x += random.randint(-3, 3)
        y += random.randint(-3, 3)

        # Small random end position (finger micro-movement)
        end_x = x + random.randint(-2, 2)
        end_y = y + random.randint(-2, 2)

        # Random duration (80-180ms, human tap duration)
        duration = random.randint(80, 180)
    else:
        end_x = x
        end_y = y
        duration = 100

    if verbose:
        print(f"👆 Tap at ({x}, {y}) using swipe method")
        print(f"   End pos: ({end_x}, {end_y}), Duration: {duration}ms")

    # Add random pre-tap delay (50-200ms)
    if humanize:
        pre_delay = random.uniform(0.05, 0.20)
        if verbose:
            print(f"   Pre-delay: {int(pre_delay * 1000)}ms")
        time.sleep(pre_delay)

    prefix = get_adb_prefix(device_id)
    result = subprocess.run(
        prefix + ["shell", "input", "swipe", str(x), str(y), str(end_x), str(end_y), str(duration)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False

    # Add random post-tap delay (30-100ms)
    if humanize:
        time.sleep(random.uniform(0.03, 0.10))

    if verbose:
        print("✅ Tap completed (swipe method)")

    return True


def real_tap_sendevent(
    x: int,
    y: int,
    device_id: str | None = None,
    verbose: bool = False,
    humanize: bool = True,
    use_su: bool = True,
) -> bool:
    """
    Perform a realistic tap using sendevent (requires root).

    Args:
        x: Screen X coordinate
        y: Screen Y coordinate
        device_id: ADB device ID
        verbose: Print debug info
        humanize: Add random variations to simulate human behavior
        use_su: Use su for root access

    Returns:
        True if successful
    """
    # Find touch device
    touch_device = get_touch_device(device_id)
    if not touch_device:
        print("❌ Could not find touch input device")
        return False

    if verbose:
        print(f"📱 Touch device: {touch_device}")

    # Get screen resolution and touch ranges
    screen_w, screen_h = get_screen_resolution(device_id)
    ranges = get_touch_range(device_id, touch_device)

    if verbose:
        print(f"📐 Screen: {screen_w}x{screen_h}")
        print(f"📐 Touch range X: 0-{ranges['x_max']}, Y: 0-{ranges['y_max']}")

    # Convert screen coordinates to touch coordinates
    touch_x = int(x * ranges["x_max"] / screen_w)
    touch_y = int(y * ranges["y_max"] / screen_h)

    # Add human-like variations
    if humanize:
        # Small random offset (±3 pixels equivalent)
        offset_x = random.randint(-3, 3) * ranges["x_max"] // screen_w
        offset_y = random.randint(-3, 3) * ranges["y_max"] // screen_h
        touch_x = max(0, min(ranges["x_max"], touch_x + offset_x))
        touch_y = max(0, min(ranges["y_max"], touch_y + offset_y))

        # Random pressure (70-100% of max)
        pressure = random.randint(int(ranges["pressure_max"] * 0.7), ranges["pressure_max"])
        touch_major = random.randint(
            int(ranges["touch_major_max"] * 0.3), int(ranges["touch_major_max"] * 0.6)
        )
    else:
        pressure = ranges["pressure_max"]
        touch_major = ranges["touch_major_max"] // 2

    if verbose:
        print(f"👆 Tap at screen ({x}, {y}) -> touch ({touch_x}, {touch_y})")
        print(f"   Pressure: {pressure}, Touch size: {touch_major}")

    # Event type constants
    EV_SYN = 0
    EV_KEY = 1
    EV_ABS = 3

    SYN_REPORT = 0

    BTN_TOUCH = 330

    ABS_MT_TRACKING_ID = 57
    ABS_MT_POSITION_X = 53
    ABS_MT_POSITION_Y = 54
    ABS_MT_TOUCH_MAJOR = 48
    ABS_MT_PRESSURE = 58

    # Build the event sequence as a shell script for efficiency
    events = [
        # Touch down
        f"sendevent {touch_device} {EV_ABS} {ABS_MT_TRACKING_ID} 0",
        f"sendevent {touch_device} {EV_ABS} {ABS_MT_POSITION_X} {touch_x}",
        f"sendevent {touch_device} {EV_ABS} {ABS_MT_POSITION_Y} {touch_y}",
        f"sendevent {touch_device} {EV_ABS} {ABS_MT_TOUCH_MAJOR} {touch_major}",
        f"sendevent {touch_device} {EV_ABS} {ABS_MT_PRESSURE} {pressure}",
        f"sendevent {touch_device} {EV_KEY} {BTN_TOUCH} 1",
        f"sendevent {touch_device} {EV_SYN} {SYN_REPORT} 0",
    ]

    # Optional: Add slight finger movement (more realistic)
    if humanize and random.random() > 0.3:
        micro_move_x = touch_x + random.randint(-2, 2) * ranges["x_max"] // screen_w
        micro_move_y = touch_y + random.randint(-2, 2) * ranges["y_max"] // screen_h
        micro_move_x = max(0, min(ranges["x_max"], micro_move_x))
        micro_move_y = max(0, min(ranges["y_max"], micro_move_y))

        events.extend(
            [
                f"sendevent {touch_device} {EV_ABS} {ABS_MT_POSITION_X} {micro_move_x}",
                f"sendevent {touch_device} {EV_ABS} {ABS_MT_POSITION_Y} {micro_move_y}",
                f"sendevent {touch_device} {EV_SYN} {SYN_REPORT} 0",
            ]
        )

    # Touch up
    events.extend(
        [
            f"sendevent {touch_device} {EV_ABS} {ABS_MT_TRACKING_ID} -1",
            f"sendevent {touch_device} {EV_KEY} {BTN_TOUCH} 0",
            f"sendevent {touch_device} {EV_SYN} {SYN_REPORT} 0",
        ]
    )

    # Execute all events in a single shell command for better timing
    shell_script = " && ".join(events)

    # Add random pre-tap delay (50-150ms)
    if humanize:
        time.sleep(random.uniform(0.05, 0.15))

    prefix = get_adb_prefix(device_id)

    # Use su if needed
    if use_su:
        result = subprocess.run(
            prefix + ["shell", "su", "-c", f"'{shell_script}'"], capture_output=True, text=True
        )
    else:
        result = subprocess.run(prefix + ["shell", shell_script], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False

    # Add random post-tap delay (30-100ms)
    if humanize:
        time.sleep(random.uniform(0.03, 0.10))

    if verbose:
        print("✅ Tap completed (sendevent method)")

    return True


def real_tap(
    x: int,
    y: int,
    device_id: str | None = None,
    verbose: bool = False,
    humanize: bool = True,
    force_method: str | None = None,
) -> bool:
    """
    Perform a realistic tap using the best available method.

    Args:
        x: Screen X coordinate
        y: Screen Y coordinate
        device_id: ADB device ID
        verbose: Print debug info
        humanize: Add random variations to simulate human behavior
        force_method: Force a specific method ('sendevent', 'swipe', or None for auto)

    Returns:
        True if successful
    """
    if force_method == "sendevent":
        return real_tap_sendevent(x, y, device_id, verbose, humanize, use_su=True)
    elif force_method == "swipe":
        return real_tap_swipe(x, y, device_id, verbose, humanize)

    # Auto-detect: try sendevent with root first, fallback to swipe
    rooted = is_device_rooted(device_id)

    if verbose:
        print(f"🔍 Device root status: {'✅ Rooted' if rooted else '❌ Not rooted'}")

    if rooted:
        if verbose:
            print("📱 Using sendevent method (root available)")
        return real_tap_sendevent(x, y, device_id, verbose, humanize, use_su=True)
    else:
        if verbose:
            print("📱 Using swipe method (no root)")
        return real_tap_swipe(x, y, device_id, verbose, humanize)


def show_device_info(device_id: str | None = None):
    """Display device touch input information."""
    print("=" * 60)
    print("📱 Device Touch Input Information")
    print("=" * 60)

    # Root status
    rooted = is_device_rooted(device_id)
    print(
        f"\n🔐 Root Status: {'✅ Rooted (sendevent available)' if rooted else '❌ Not rooted (using swipe fallback)'}"
    )

    # Screen resolution
    screen_w, screen_h = get_screen_resolution(device_id)
    print(f"📐 Screen Resolution: {screen_w} x {screen_h}")

    # Touch device
    touch_device = get_touch_device(device_id)
    if touch_device:
        print(f"🎯 Touch Device: {touch_device}")
        ranges = get_touch_range(device_id, touch_device)
        print(f"   X Range: 0 - {ranges['x_max']}")
        print(f"   Y Range: 0 - {ranges['y_max']}")
        print(f"   Pressure Max: {ranges['pressure_max']}")
        print(f"   Touch Major Max: {ranges['touch_major_max']}")
    else:
        print("❌ Touch device not found")

    # Recommended method
    print(
        f"\n💡 Recommended tap method: {'sendevent (best anti-detection)' if rooted else 'swipe (moderate anti-detection)'}"
    )

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Real tap simulation to bypass anti-bot detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show device info
  python real_tap.py --info
  
  # Tap at coordinates (500, 800)
  python real_tap.py --x 500 --y 800
  
  # Tap with verbose output
  python real_tap.py --x 500 --y 800 -v
  
  # Tap without humanization (exact coordinates)
  python real_tap.py --x 500 --y 800 --no-humanize
  
  # Specify device
  python real_tap.py --x 500 --y 800 --device 3607f6cc
        """,
    )

    parser.add_argument("--info", action="store_true", help="Show device touch info")
    parser.add_argument("--x", type=int, help="X coordinate")
    parser.add_argument("--y", type=int, help="Y coordinate")
    parser.add_argument("--device", "-d", type=str, help="ADB device ID")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-humanize", action="store_true", help="Disable human-like variations")

    args = parser.parse_args()

    if args.info:
        show_device_info(args.device)
        return 0

    if args.x is None or args.y is None:
        parser.print_help()
        print("\n❌ Error: --x and --y are required for tapping")
        return 1

    success = real_tap(
        x=args.x,
        y=args.y,
        device_id=args.device,
        verbose=args.verbose,
        humanize=not args.no_humanize,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
