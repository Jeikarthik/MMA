"""Hardware/resource safety checks."""

from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess

from mma.config import SafetyCaps


@dataclass(frozen=True)
class ResourceStatus:
    safe_for_local: bool
    hard_stop: bool
    messages: list[str]


def check_resources(caps: SafetyCaps) -> ResourceStatus:
    """Check conservative local execution safety using built-in Windows-friendly probes."""

    messages: list[str] = []
    hard_stop = False

    memory = shutil.disk_usage("/")  # fallback placeholder for environments without psutil
    # The stdlib has no direct cross-platform RAM API. Try PowerShell CIM on Windows.
    ram = _windows_ram_status()
    if ram is not None:
        free_gb, pressure_pct = ram
        if free_gb < caps.min_free_ram_warning_gb:
            messages.append(f"free RAM low: {free_gb:.1f}GB")
        if free_gb < caps.min_free_ram_hard_stop_gb:
            hard_stop = True
            messages.append(f"free RAM hard stop: {free_gb:.1f}GB")
        if pressure_pct >= caps.memory_pressure_warning_pct:
            messages.append(f"memory pressure high: {pressure_pct:.0f}%")
        if pressure_pct >= caps.memory_pressure_hard_stop_pct:
            hard_stop = True
            messages.append(f"memory pressure hard stop: {pressure_pct:.0f}%")
    else:
        messages.append(f"RAM probe unavailable; disk free fallback {memory.free // (1024**3)}GB")

    temp = _nvidia_gpu_temp()
    if temp is not None:
        if temp >= caps.gpu_temp_warning_c:
            messages.append(f"GPU temperature warning: {temp}C")
        if temp >= caps.gpu_temp_hard_stop_c:
            hard_stop = True
            messages.append(f"GPU temperature hard stop: {temp}C")

    return ResourceStatus(safe_for_local=not hard_stop, hard_stop=hard_stop, messages=messages)


def _windows_ram_status() -> tuple[float, float] | None:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$os=Get-CimInstance Win32_OperatingSystem; "
            "$free=[double]$os.FreePhysicalMemory*1KB; "
            "$total=[double]$os.TotalVisibleMemorySize*1KB; "
            "$pressure=(1-($free/$total))*100; "
            "Write-Output \"$($free/1GB),$pressure\""
        ),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or "," not in result.stdout:
        return None
    try:
        free, pressure = result.stdout.strip().split(",", 1)
        return float(free), float(pressure)
    except ValueError:
        return None


def _nvidia_gpu_temp() -> int | None:
    command = [
        "nvidia-smi",
        "--query-gpu=temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        return int(result.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return None
