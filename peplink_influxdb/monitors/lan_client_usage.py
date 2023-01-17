from datetime import datetime
from typing import Generator

from peplink_api.services import PepLinkClientService

from .base import Measurement, Monitor


class LANClientUsageMonitor(Monitor):
    refresh_rate: int = 30  # seconds

    def seed_hostname_cache(self, peplink_client: PepLinkClientService) -> None:
        clients = self.peplink.client_status(weight="lite")["list"]
        for client in clients:
            self.global_state.hostname_cache[client["mac"]] = client["name"]

    def update(
        self, peplink_client: PepLinkClientService
    ) -> Generator[Measurement, None, None]:
        if not self.global_state.hostname_cache:
            self.seed_hostname_cache(peplink_client)

        month_start = datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        usage = peplink_client.client_bandwidth_usage(
            period="monthly", from_=month_start
        )
        clients = usage["monthly"][month_start.date().isoformat()]
        for client in clients:
            mac = client["mac"]
            tags = {"ip": client["ip"], "mac": mac}
            hostname = self.global_state.hostname_cache.get(mac)
            if hostname:
                tags["name"] = hostname
            yield Measurement(
                "client.usage",
                tags,
                {
                    "upload": client["upload"],
                    "download": client["download"],
                },
            )
