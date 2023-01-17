from typing import Generator

from peplink_api.services import PepLinkClientService

from .base import Measurement, Monitor


class LanClientMonitor(Monitor):
    refresh_rate: int = 1  # seconds

    def update(self, peplink_client: PepLinkClientService) -> Generator[Measurement, None, None]:
        clients = peplink_client.client_status(weight="full", active_only=True)["list"]
        for client in clients:
            mac = client["mac"]
            name = client["name"]
            self.global_state.hostname_cache[mac] = name
            keys = {
                "ip": client["ip"],
                "mac": mac,
                "name": name,
            }
            if client["connectionType"] == "wireless":
                yield Measurement(
                    "client.signal",
                    keys,
                    client["signal"],
                )

            assert client["speed"]["unit"] == "kbps"
            yield Measurement(
                "client.speed",
                keys,
                {
                    "upload": client["speed"]["upload"],
                    "download": client["speed"]["download"],
                },
            )
