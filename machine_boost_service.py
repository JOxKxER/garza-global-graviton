"""
machine_boost_service.py - Windows service wrapper around
machine_boost_supervisor.py, so it starts automatically at machine boot
(not just at user logon) and keeps running in the background.

One-time setup (run in an elevated/Administrator PowerShell -- service
install/start requires admin rights that this assistant cannot grant itself):

    pip install pywin32
    python machine_boost_service.py install
    python machine_boost_service.py start

To check on it later:
    python machine_boost_service.py status   (or: Get-Service GGGMachineBoost)
    Get-Content logs\\machine_boost_supervisor.log -Tail 50 -Wait

To stop/remove it:
    python machine_boost_service.py stop
    python machine_boost_service.py remove
"""

from __future__ import annotations

import threading

import servicemanager
import win32event
import win32service
import win32serviceutil

import machine_boost_supervisor


class MachineBoostService(win32serviceutil.ServiceFramework):
    _svc_name_ = "GGGMachineBoost"
    _svc_display_name_ = "Garza Global Graviton - Machine Boost Supervisor"
    _svc_description_ = (
        "Runs watchdog_daemon, system_watchdog, snapshot_daemon, "
        "mesh_ping_daemon, and health_monitor on a schedule at machine startup."
    )

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = threading.Event()
        self._wait_handle = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.stop_event.set()
        win32event.SetEvent(self._wait_handle)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        supervisor_thread = threading.Thread(
            target=machine_boost_supervisor.run, args=(self.stop_event,), daemon=True
        )
        supervisor_thread.start()
        # Block the service's main thread until SvcStop signals us.
        win32event.WaitForSingleObject(self._wait_handle, win32event.INFINITE)
        supervisor_thread.join(timeout=30)


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(MachineBoostService)
