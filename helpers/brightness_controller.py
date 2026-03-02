import os
import subprocess
from pathlib import Path


class BrightnessController:
    """
    Controls display brightness with backend fallbacks:
    1) Linux backlight sysfs (/sys/class/backlight)
    2) xrandr software brightness (X11)
    """

    def __init__(self, dim_percent=1):
        self.dim_percent = max(1, min(100, int(dim_percent)))
        self._backend = None
        self._sysfs_brightness_path = None
        self._sysfs_original_brightness = None
        self._sysfs_max_brightness = None
        self._xrandr_outputs = []

        if self._init_sysfs_backend():
            self._backend = 'sysfs'
        elif self._init_xrandr_backend():
            self._backend = 'xrandr'

    @property
    def backend(self):
        return self._backend

    @property
    def available(self):
        return self._backend is not None

    def dim(self):
        if self._backend == 'sysfs':
            return self._set_sysfs_brightness_percent(self.dim_percent)
        if self._backend == 'xrandr':
            return self._set_xrandr_brightness(self.dim_percent / 100.0)
        return False

    def restore(self):
        if self._backend == 'sysfs':
            return self._restore_sysfs_brightness()
        if self._backend == 'xrandr':
            return self._set_xrandr_brightness(1.0)
        return False

    def _run_command(self, cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, check=False)
        except Exception:
            return None

    def _init_sysfs_backend(self):
        base = Path('/sys/class/backlight')
        if not base.exists():
            return False

        for device in sorted(base.iterdir()):
            brightness_path = device / 'brightness'
            max_path = device / 'max_brightness'
            if not brightness_path.exists() or not max_path.exists():
                continue
            if not os.access(brightness_path, os.W_OK):
                continue
            try:
                current = int(brightness_path.read_text().strip())
                maximum = int(max_path.read_text().strip())
            except Exception:
                continue
            if maximum <= 0:
                continue

            self._sysfs_brightness_path = brightness_path
            self._sysfs_original_brightness = current
            self._sysfs_max_brightness = maximum
            return True

        return False

    def _set_sysfs_brightness_percent(self, percent):
        if not self._sysfs_brightness_path or not self._sysfs_max_brightness:
            return False

        target = int(self._sysfs_max_brightness * (percent / 100.0))
        target = max(1, min(self._sysfs_max_brightness, target))
        try:
            self._sysfs_brightness_path.write_text(f'{target}\n')
            return True
        except Exception:
            return False

    def _restore_sysfs_brightness(self):
        if not self._sysfs_brightness_path:
            return False
        target = self._sysfs_original_brightness
        if target is None:
            target = self._sysfs_max_brightness
        try:
            self._sysfs_brightness_path.write_text(f'{int(target)}\n')
            return True
        except Exception:
            return False

    def _init_xrandr_backend(self):
        result = self._run_command(['xrandr', '--query'])
        if not result or result.returncode != 0:
            return False

        outputs = []
        for line in result.stdout.splitlines():
            if ' connected' in line:
                output_name = line.split()[0]
                outputs.append(output_name)

        self._xrandr_outputs = outputs
        return len(self._xrandr_outputs) > 0

    def _set_xrandr_brightness(self, value):
        if not self._xrandr_outputs:
            return False

        value = max(0.1, min(1.0, float(value)))
        success = True
        for output in self._xrandr_outputs:
            result = self._run_command([
                'xrandr',
                '--output',
                output,
                '--brightness',
                f'{value:.2f}',
            ])
            if not result or result.returncode != 0:
                success = False

        return success
