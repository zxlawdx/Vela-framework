"""Qt must choose an available display before the first native window."""

from vela.core.window import configure_linux_display


def test_wayland_with_xwayland_uses_xcb():
    env = {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"}
    configure_linux_display(env, "linux")
    assert env["QT_QPA_PLATFORM"] == "xcb"


def test_explicit_backend_is_preserved():
    for backend in ("wayland", "offscreen", "xcb"):
        env = {"DISPLAY": ":0", "QT_QPA_PLATFORM": backend}
        configure_linux_display(env, "linux")
        assert env["QT_QPA_PLATFORM"] == backend


def test_native_wayland_without_xwayland_is_preserved():
    env = {"WAYLAND_DISPLAY": "wayland-0"}
    configure_linux_display(env, "linux")
    assert "QT_QPA_PLATFORM" not in env


def test_other_platforms_are_unchanged():
    env = {"DISPLAY": ":0"}
    configure_linux_display(env, "win32")
    assert "QT_QPA_PLATFORM" not in env
