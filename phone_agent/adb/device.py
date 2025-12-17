"""Device control utilities for Android automation."""

import os
import random
import subprocess
import time
from typing import List, Optional, Tuple

from phone_agent.config.apps import APP_PACKAGES
from phone_agent.config.timing import TIMING_CONFIG

# Cache for device info
_device_cache: dict = {}


def _is_device_rooted(device_id: str | None = None) -> bool:
    """Check if device has root access."""
    cache_key = f"rooted_{device_id}"
    if cache_key in _device_cache:
        return _device_cache[cache_key]

    adb_prefix = _get_adb_prefix(device_id)
    result = subprocess.run(
        adb_prefix + ["shell", "su", "-c", "id"], capture_output=True, text=True
    )
    rooted = result.returncode == 0 and "uid=0" in result.stdout
    _device_cache[cache_key] = rooted
    return rooted


def _get_touch_device(device_id: str | None = None) -> str | None:
    """Find the touch input device path."""
    cache_key = f"touch_device_{device_id}"
    if cache_key in _device_cache:
        return _device_cache[cache_key]

    adb_prefix = _get_adb_prefix(device_id)
    result = subprocess.run(
        adb_prefix + ["shell", "getevent", "-pl"], capture_output=True, text=True
    )

    current_device = None
    for line in result.stdout.split("\n"):
        if line.startswith("add device"):
            parts = line.split(":")
            if len(parts) >= 2:
                current_device = parts[1].strip()
        elif "ABS_MT_POSITION_X" in line and current_device:
            _device_cache[cache_key] = current_device
            return current_device

    return None


def _get_screen_resolution(device_id: str | None = None) -> tuple[int, int]:
    """Get device screen resolution."""
    cache_key = f"resolution_{device_id}"
    if cache_key in _device_cache:
        return _device_cache[cache_key]

    adb_prefix = _get_adb_prefix(device_id)
    result = subprocess.run(adb_prefix + ["shell", "wm", "size"], capture_output=True, text=True)

    for line in result.stdout.split("\n"):
        if "size" in line.lower():
            parts = line.split(":")
            if len(parts) >= 2:
                size = parts[1].strip()
                w, h = size.split("x")
                resolution = (int(w), int(h))
                _device_cache[cache_key] = resolution
                return resolution

    return (1080, 2400)


def _sendevent_tap(
    x: int,
    y: int,
    device_id: str | None = None,
    humanize: bool = True,
) -> bool:
    """Perform a realistic tap using sendevent (requires root)."""
    touch_device = _get_touch_device(device_id)
    if not touch_device:
        return False

    screen_w, screen_h = _get_screen_resolution(device_id)

    # Add human-like variations
    if humanize:
        x += random.randint(-3, 3)
        y += random.randint(-3, 3)
        pressure = random.randint(180, 255)
        touch_major = random.randint(80, 150)
    else:
        pressure = 255
        touch_major = 100

    # Event constants
    EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
    SYN_REPORT, BTN_TOUCH = 0, 330
    ABS_MT_TRACKING_ID, ABS_MT_POSITION_X, ABS_MT_POSITION_Y = 57, 53, 54
    ABS_MT_TOUCH_MAJOR, ABS_MT_PRESSURE = 48, 58

    # Build event sequence
    events = [
        f"sendevent {touch_device} {EV_ABS} {ABS_MT_TRACKING_ID} 0",
        f"sendevent {touch_device} {EV_ABS} {ABS_MT_POSITION_X} {x}",
        f"sendevent {touch_device} {EV_ABS} {ABS_MT_POSITION_Y} {y}",
        f"sendevent {touch_device} {EV_ABS} {ABS_MT_TOUCH_MAJOR} {touch_major}",
        f"sendevent {touch_device} {EV_ABS} {ABS_MT_PRESSURE} {pressure}",
        f"sendevent {touch_device} {EV_KEY} {BTN_TOUCH} 1",
        f"sendevent {touch_device} {EV_SYN} {SYN_REPORT} 0",
    ]

    # Add micro movement for realism
    if humanize and random.random() > 0.3:
        micro_x = x + random.randint(-2, 2)
        micro_y = y + random.randint(-2, 2)
        events.extend(
            [
                f"sendevent {touch_device} {EV_ABS} {ABS_MT_POSITION_X} {micro_x}",
                f"sendevent {touch_device} {EV_ABS} {ABS_MT_POSITION_Y} {micro_y}",
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

    shell_script = " && ".join(events)

    # Random pre-tap delay
    if humanize:
        time.sleep(random.uniform(0.05, 0.15))

    adb_prefix = _get_adb_prefix(device_id)
    result = subprocess.run(
        adb_prefix + ["shell", "su", "-c", f"'{shell_script}'"], capture_output=True, text=True
    )

    return result.returncode == 0


def get_current_app(device_id: str | None = None) -> str:
    """
    Get the currently focused app name.

    Args:
        device_id: Optional ADB device ID for multi-device setups.

    Returns:
        The app name if recognized, otherwise "System Home".
    """
    adb_prefix = _get_adb_prefix(device_id)

    result = subprocess.run(
        adb_prefix + ["shell", "dumpsys", "window"], capture_output=True, text=True
    )
    output = result.stdout

    # Parse window focus info
    for line in output.split("\n"):
        if "mCurrentFocus" in line or "mFocusedApp" in line:
            for app_name, package in APP_PACKAGES.items():
                if package in line:
                    return app_name

    return "System Home"


def tap(
    x: int,
    y: int,
    device_id: str | None = None,
    delay: float | None = None,
    use_sendevent: bool = True,
) -> None:
    """
    Tap at the specified coordinates.

    Args:
        x: X coordinate.
        y: Y coordinate.
        device_id: Optional ADB device ID.
        delay: Delay in seconds after tap. If None, uses configured default.
        use_sendevent: If True and device is rooted, use sendevent for anti-detection.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_tap_delay

    # Try sendevent method if device is rooted (better anti-detection)
    if use_sendevent and _is_device_rooted(device_id):
        if _sendevent_tap(x, y, device_id, humanize=True):
            time.sleep(delay)
            return

    # Fallback to regular input tap
    adb_prefix = _get_adb_prefix(device_id)
    subprocess.run(adb_prefix + ["shell", "input", "tap", str(x), str(y)], capture_output=True)
    time.sleep(delay)


def double_tap(x: int, y: int, device_id: str | None = None, delay: float | None = None) -> None:
    """
    Double tap at the specified coordinates.

    Args:
        x: X coordinate.
        y: Y coordinate.
        device_id: Optional ADB device ID.
        delay: Delay in seconds after double tap. If None, uses configured default.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_double_tap_delay

    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(adb_prefix + ["shell", "input", "tap", str(x), str(y)], capture_output=True)
    time.sleep(TIMING_CONFIG.device.double_tap_interval)
    subprocess.run(adb_prefix + ["shell", "input", "tap", str(x), str(y)], capture_output=True)
    time.sleep(delay)


def long_press(
    x: int,
    y: int,
    duration_ms: int = 3000,
    device_id: str | None = None,
    delay: float | None = None,
) -> None:
    """
    Long press at the specified coordinates.

    Args:
        x: X coordinate.
        y: Y coordinate.
        duration_ms: Duration of press in milliseconds.
        device_id: Optional ADB device ID.
        delay: Delay in seconds after long press. If None, uses configured default.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_long_press_delay

    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(duration_ms)],
        capture_output=True,
    )
    time.sleep(delay)


def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration_ms: int | None = None,
    device_id: str | None = None,
    delay: float | None = None,
) -> None:
    """
    Swipe from start to end coordinates.

    Args:
        start_x: Starting X coordinate.
        start_y: Starting Y coordinate.
        end_x: Ending X coordinate.
        end_y: Ending Y coordinate.
        duration_ms: Duration of swipe in milliseconds (auto-calculated if None).
        device_id: Optional ADB device ID.
        delay: Delay in seconds after swipe. If None, uses configured default.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_swipe_delay

    adb_prefix = _get_adb_prefix(device_id)

    if duration_ms is None:
        # Calculate duration based on distance
        dist_sq = (start_x - end_x) ** 2 + (start_y - end_y) ** 2
        duration_ms = int(dist_sq / 1000)
        duration_ms = max(1000, min(duration_ms, 2000))  # Clamp between 1000-2000ms

    subprocess.run(
        adb_prefix
        + [
            "shell",
            "input",
            "swipe",
            str(start_x),
            str(start_y),
            str(end_x),
            str(end_y),
            str(duration_ms),
        ],
        capture_output=True,
    )
    time.sleep(delay)


def back(device_id: str | None = None, delay: float | None = None) -> None:
    """
    Press the back button.

    Args:
        device_id: Optional ADB device ID.
        delay: Delay in seconds after pressing back. If None, uses configured default.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_back_delay

    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(adb_prefix + ["shell", "input", "keyevent", "4"], capture_output=True)
    time.sleep(delay)


def home(device_id: str | None = None, delay: float | None = None) -> None:
    """
    Press the home button.

    Args:
        device_id: Optional ADB device ID.
        delay: Delay in seconds after pressing home. If None, uses configured default.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_home_delay

    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(adb_prefix + ["shell", "input", "keyevent", "KEYCODE_HOME"], capture_output=True)
    time.sleep(delay)


def wake_screen(device_id: str | None = None) -> bool:
    """
    Wake up the screen if it's off.

    Args:
        device_id: Optional ADB device ID.

    Returns:
        True if the screen was woken up (was off), False if already on.
    """
    adb_prefix = _get_adb_prefix(device_id)

    # Check if screen is already on
    result = subprocess.run(
        adb_prefix + ["shell", "dumpsys", "power"],
        capture_output=True,
        text=True,
    )

    # Check for screen state in dumpsys output
    is_screen_on = "mWakefulness=Awake" in result.stdout or "Display Power: state=ON" in result.stdout

    if is_screen_on:
        print("📱 Screen is already on")
        return False

    # Wake up the screen using KEYCODE_WAKEUP (224)
    subprocess.run(
        adb_prefix + ["shell", "input", "keyevent", "KEYCODE_WAKEUP"],
        capture_output=True,
    )
    time.sleep(0.5)
    print("📱 Screen woken up")
    return True


def sleep_screen(device_id: str | None = None) -> bool:
    """
    Turn off the screen (put device to sleep).

    Args:
        device_id: Optional ADB device ID.

    Returns:
        True if the screen was turned off (was on), False if already off.
    """
    adb_prefix = _get_adb_prefix(device_id)

    # Check if screen is already off
    result = subprocess.run(
        adb_prefix + ["shell", "dumpsys", "power"],
        capture_output=True,
        text=True,
    )

    # Check for screen state in dumpsys output
    is_screen_on = "mWakefulness=Awake" in result.stdout or "Display Power: state=ON" in result.stdout

    if not is_screen_on:
        print("📱 Screen is already off")
        return False

    # Turn off the screen using KEYCODE_SLEEP (223)
    subprocess.run(
        adb_prefix + ["shell", "input", "keyevent", "KEYCODE_SLEEP"],
        capture_output=True,
    )
    time.sleep(0.3)
    print("📱 Screen turned off")
    return True


def unlock_screen(device_id: str | None = None, swipe_up: bool = True) -> bool:
    """
    Unlock the screen by waking it and performing a swipe gesture.

    This function handles basic lock screens that only require a swipe.
    For PIN/pattern/password locks, manual intervention is required.

    Args:
        device_id: Optional ADB device ID.
        swipe_up: If True, swipe up to unlock. If False, swipe from left to right.

    Returns:
        True if unlock attempt was made, False if screen was already unlocked.
    """
    adb_prefix = _get_adb_prefix(device_id)

    # First, wake up the screen
    wake_screen(device_id)
    time.sleep(0.3)

    # Check if device is already unlocked
    result = subprocess.run(
        adb_prefix + ["shell", "dumpsys", "window"],
        capture_output=True,
        text=True,
    )

    # Check if lock screen is showing
    is_locked = "mDreamingLockscreen=true" in result.stdout or "isStatusBarKeyguard=true" in result.stdout

    if not is_locked:
        print("🔓 Screen is already unlocked")
        return False

    # Get screen resolution for swipe
    screen_w, screen_h = _get_screen_resolution(device_id)

    if swipe_up:
        # Swipe up from bottom center to middle
        start_x = screen_w // 2
        start_y = int(screen_h * 0.85)
        end_x = screen_w // 2
        end_y = int(screen_h * 0.3)
    else:
        # Swipe from left to right
        start_x = int(screen_w * 0.2)
        start_y = screen_h // 2
        end_x = int(screen_w * 0.8)
        end_y = screen_h // 2

    subprocess.run(
        adb_prefix + [
            "shell", "input", "swipe",
            str(start_x), str(start_y),
            str(end_x), str(end_y),
            "300"
        ],
        capture_output=True,
    )

    time.sleep(0.5)
    print("🔓 Unlock swipe performed")
    return True


def launch_app(app_name: str, device_id: str | None = None, delay: float | None = None) -> bool:
    """
    Launch an app by name.

    Args:
        app_name: The app name (must be in APP_PACKAGES).
        device_id: Optional ADB device ID.
        delay: Delay in seconds after launching. If None, uses configured default.

    Returns:
        True if app was launched, False if app not found.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_launch_delay

    if app_name not in APP_PACKAGES:
        return False

    adb_prefix = _get_adb_prefix(device_id)
    package = APP_PACKAGES[app_name]

    subprocess.run(
        adb_prefix
        + [
            "shell",
            "monkey",
            "-p",
            package,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ],
        capture_output=True,
    )
    time.sleep(delay)
    return True


def _get_adb_prefix(device_id: str | None) -> list:
    """Get ADB command prefix with optional device specifier."""
    if device_id:
        return ["adb", "-s", device_id]
    return ["adb"]
