"""Reboot Aqara gateway hardware via telnet."""
import logging

from .utils import Utils

_LOGGER = logging.getLogger(__name__)


def _hub_model(gateway) -> str:
    """Coordinator model for telnet shell class (not first child device)."""
    model = (getattr(gateway, "_model", None) or "").strip()
    if model:
        return model
    for dev in getattr(gateway, "devices", {}).values():
        if dev.get("type") == "gateway":
            return (dev.get("model") or "").strip()
    return ""


def reboot_gateway_via_telnet(gateway) -> None:
    """Run sync then reboot; connection drops as expected."""
    shell = None
    host = getattr(gateway, "host", "?")
    model = _hub_model(gateway)
    if not model:
        msg = "Gateway model unknown; cannot select telnet shell"
        _LOGGER.error("%s host=%s", msg, host)
        raise RuntimeError(msg)

    device_name = Utils.get_device_name(model).lower()
    try:
        shell = gateway._get_shell(device_name)
        shell.login()
        _LOGGER.warning(
            "Gateway hardware reboot via telnet host=%s model=%s",
            host,
            model,
        )
        shell.run_command("sync", read_timeout=8)
        shell.run_command("reboot", read_timeout=5)
    except Exception:
        _LOGGER.exception("Gateway reboot failed host=%s", host)
        raise
    finally:
        if shell is not None:
            try:
                shell.close()
            except Exception:
                pass
