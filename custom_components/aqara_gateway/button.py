"""Gateway buttons: reboot, speaker play, and Aqara device actions."""

import logging
from functools import partial

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway
from .core.gateway_reboot import reboot_gateway_via_telnet
from .core.gateway_speaker import SPEAKER_LABEL_TO_FILE, play_speaker_scene

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up button platform."""

    def setup(gateway: Gateway, device: dict, attr: str):
        if attr == 'reboot_gateway':
            async_add_entities([GatewayHubRebootButton(gateway, device, attr)])
        elif attr == 'speaker_play':
            _LOGGER.info(
                "button setup: registering Speaker Play gateway=%s model=%s did=%s",
                gateway.host,
                device.get("model"),
                device.get("did"),
            )
            async_add_entities([GatewaySpeakerPlayButton(gateway, device, attr)])
        else:
            async_add_entities([GatewayButton(gateway, device, attr)])

    gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    gateway.add_setup('button', setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """unload entry"""
    return True


class GatewayHubRebootButton(GatewayGenericDevice, ButtonEntity):
    """Hardware reboot via telnet (sync; reboot)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_translation_key = 'reboot_gateway'
    _attr_icon = 'mdi:restart'

    def __init__(self, gateway: Gateway, device: dict, attr: str):
        super().__init__(gateway, device, attr)

    async def async_added_to_hass(self) -> None:
        """No MQTT subscription."""

    async def async_will_remove_from_hass(self) -> None:
        """Nothing to unsubscribe."""

    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(
            reboot_gateway_via_telnet,
            self.gateway,
        )


class GatewaySpeakerPlayButton(GatewayGenericDevice, ButtonEntity):
    """Play selected WAV once (telnet + aplay)."""

    _attr_icon = "mdi:play-circle"

    def __init__(self, gateway: Gateway, device: dict, attr: str):
        super().__init__(gateway, device, attr)

    async def async_press(self) -> None:
        _LOGGER.info(
            "Speaker Play pressed entity=%s host=%s (queue if busy)",
            self.entity_id,
            self.gateway.host,
        )
        async with self.gateway.speaker_play_lock:
            snap = dict(self.gateway._speaker_snapshot)
            label = snap.get('label', 'Doorbell 1')
            wav = SPEAKER_LABEL_TO_FILE.get(label, 'door_bell_1.wav')
            _LOGGER.info(
                "Speaker Play run entity=%s snapshot=%r -> wav=%r",
                self.entity_id,
                snap,
                wav,
            )
            _LOGGER.debug(
                "Speaker Play executor_job submit entity=%s", self.entity_id
            )
            try:
                await self.hass.async_add_executor_job(
                    partial(play_speaker_scene, self.gateway, wav)
                )
            except Exception:
                _LOGGER.exception(
                    "Speaker Play executor failed entity=%s host=%s",
                    self.entity_id,
                    self.gateway.host,
                )
                raise
            _LOGGER.debug(
                "Speaker Play executor_job done entity=%s", self.entity_id
            )


class GatewayButton(GatewayGenericDevice, ButtonEntity):
    """Representation of an Aqara button entity (e.g. find_device)."""

    @property
    def icon(self):
        """Return icon."""
        if self._attr == 'find_device':
            return 'mdi:radar'
        return 'mdi:gesture-tap-button'

    def update(self, data: dict):
        """Buttons are stateless."""
        return None

    async def async_press(self) -> None:
        """Press the button."""
        self.gateway.send(self.device, {self._attr: 1})
