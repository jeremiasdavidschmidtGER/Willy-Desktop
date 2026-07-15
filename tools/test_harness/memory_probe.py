"""Process working-set (RSS) measurement for the soak/profiling tools.

Uses ctypes + psapi directly instead of a new third-party dependency
(no `psutil` in pyproject.toml). This is QA tooling outside `src/willy/`,
so ARCHITECTURE.md §7's "nothing else imports ctypes" rule — which isolates
raw Win32 calls to `platform/win32.py` for the *product* package — does not
apply here; `willy` itself still imports no ctypes anywhere.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def current_rss_bytes() -> int:
    """Current process working-set size — Windows' closest analogue to RSS."""
    if sys.platform != "win32":
        raise NotImplementedError("current_rss_bytes is Windows-only (target platform)")
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    # Explicit argtypes/restype: GetCurrentProcess()'s pseudo-handle is a
    # 64-bit value that ctypes' default (32-bit int) restype would truncate.
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
    handle = kernel32.GetCurrentProcess()
    ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
    if not ok:
        raise OSError("GetProcessMemoryInfo failed")
    return counters.WorkingSetSize
