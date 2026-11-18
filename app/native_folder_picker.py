# AI contribution: 50% or more AI-generated
"""Windows Explorer folder selection in an isolated, dependency-free STA process."""

import ctypes
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
from uuid import UUID

PICKER_TIMEOUT_SECONDS = 300


def open_folder_dialog(initial_path: str | None) -> str | None:
    """Keep the API's worker threads free of COM state and hide the helper console."""
    result = subprocess.run(
        # Windows venv redirectors spawn another process. Use the base runtime
        # for this stdlib-only helper so a timeout closes the actual dialog.
        [
            getattr(sys, "_base_executable", None) or sys.executable,
            "-m",
            "app.native_folder_picker",
        ],
        input=json.dumps({"initial_path": initial_path}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=PICKER_TIMEOUT_SECONDS,
        cwd=Path(__file__).resolve().parents[1],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=True,
    )
    data = json.loads(result.stdout)
    if not isinstance(data, dict) or "path" not in data:
        raise ValueError("Invalid picker response")
    path = data["path"]
    if path is not None and (not isinstance(path, str) or not path):
        raise ValueError("Invalid picker path")
    return path if isinstance(path, str) else None


class GUID(ctypes.Structure):
    _fields_ = [
        ("data1", ctypes.c_uint32),
        ("data2", ctypes.c_uint16),
        ("data3", ctypes.c_uint16),
        ("data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def parse(cls, value: str) -> "GUID":
        return cls.from_buffer_copy(UUID(value).bytes_le)


def choose_windows_folder(initial_path: str | None) -> str | None:
    """Use IFileOpenDialog with FOS_PICKFOLDERS (the modern Explorer dialog).

    The method slots below follow IUnknown -> IModalWindow -> IFileDialog;
    IShellItem::GetDisplayName returns a COM-allocated filesystem path.
    https://learn.microsoft.com/windows/win32/shell/common-file-dialog
    """
    if sys.platform != "win32":
        raise OSError("The native workspace picker requires Windows")
    ole32 = ctypes.WinDLL("ole32")
    shell32 = ctypes.WinDLL("shell32")
    pointer = ctypes.c_void_p
    uint = ctypes.c_uint32
    guid_pointer = ctypes.POINTER(GUID)
    out_pointer = ctypes.POINTER(pointer)
    ole32.CoInitializeEx.argtypes = [pointer, uint]
    ole32.CoInitializeEx.restype = ctypes.c_long
    ole32.CoCreateInstance.argtypes = [
        guid_pointer,
        pointer,
        uint,
        guid_pointer,
        out_pointer,
    ]
    ole32.CoCreateInstance.restype = ctypes.c_long
    ole32.CoTaskMemFree.argtypes = [pointer]
    ole32.CoTaskMemFree.restype = None
    ole32.CoUninitialize.argtypes = []
    ole32.CoUninitialize.restype = None
    shell32.SHCreateItemFromParsingName.argtypes = [
        ctypes.c_wchar_p,
        pointer,
        guid_pointer,
        out_pointer,
    ]
    shell32.SHCreateItemFromParsingName.restype = ctypes.c_long

    def check(result: int) -> None:
        if result < 0:
            raise OSError("Windows folder picker failed")

    def method(interface: ctypes.c_void_p, slot: int, *argtypes: Any) -> Any:
        table = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(pointer))).contents
        return ctypes.WINFUNCTYPE(ctypes.c_long, pointer, *argtypes)(table[slot])

    dialog, initial, selected, display = pointer(), pointer(), pointer(), pointer()
    clsid = GUID.parse("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")
    dialog_iid = GUID.parse("D57C7288-D4AD-4768-BE02-9D969532D960")
    item_iid = GUID.parse("43826D1E-E718-42EE-BC55-A1E261C37BFE")
    check(ole32.CoInitializeEx(None, 0x2 | 0x4))
    try:
        check(
            ole32.CoCreateInstance(
                ctypes.byref(clsid),
                None,
                1,
                ctypes.byref(dialog_iid),
                ctypes.byref(dialog),
            )
        )
        options = uint()
        check(method(dialog, 10, ctypes.POINTER(uint))(dialog, ctypes.byref(options)))
        # Pick folders, return real filesystem paths, require an existing path,
        # and leave the API process's working directory unchanged.
        check(
            method(dialog, 9, uint)(dialog, options.value | 0x20 | 0x40 | 0x800 | 0x8)
        )
        check(method(dialog, 17, ctypes.c_wchar_p)(dialog, "Select workspace folder"))
        check(method(dialog, 18, ctypes.c_wchar_p)(dialog, "Select folder"))
        if initial_path:
            result = shell32.SHCreateItemFromParsingName(
                initial_path, None, ctypes.byref(item_iid), ctypes.byref(initial)
            )
            if result >= 0:
                check(method(dialog, 12, pointer)(dialog, initial))
        result = method(dialog, 3, pointer)(dialog, None)
        if result & 0xFFFFFFFF == 0x800704C7:  # HRESULT_FROM_WIN32(ERROR_CANCELLED)
            return None
        check(result)
        check(method(dialog, 20, out_pointer)(dialog, ctypes.byref(selected)))
        check(
            method(selected, 5, uint, out_pointer)(
                selected,
                0x80058000,
                ctypes.byref(display),  # SIGDN_FILESYSPATH
            )
        )
        return ctypes.wstring_at(display)
    finally:
        if display:
            ole32.CoTaskMemFree(display)
        for interface in (selected, initial, dialog):
            if interface:
                method(interface, 2)(interface)  # IUnknown::Release
        ole32.CoUninitialize()


if __name__ == "__main__":
    try:
        payload = json.loads(sys.stdin.read(16384))
        json.dump({"path": choose_windows_folder(payload["initial_path"])}, sys.stdout)
    except Exception:
        # Never send Windows exception text, paths or private shell details to the UI.
        sys.exit(1)
