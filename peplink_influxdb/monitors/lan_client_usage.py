from datetime import datetime
from typing import Generator
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from peplink_api.services import PepLinkClientService

from .base import Measurement, Monitor


class LANClientUsageMonitor(Monitor):
    refresh_rate: int = 30  # seconds

    def lookup_device_timezone(self, peplink_client):
        time = peplink_client.time_config()
        self.global_state.time_zone = time["timeZone"]

    def seed_hostname_cache(self, peplink_client: PepLinkClientService) -> None:
        clients = self.peplink.client_status(weight="lite")["list"]
        for client in clients:
            self.global_state.hostname_cache[client["mac"]] = client["name"]

    def update(
        self, peplink_client: PepLinkClientService
    ) -> Generator[Measurement, None, None]:
        if not self.global_state.hostname_cache:
            self.seed_hostname_cache(peplink_client)
        if not self.global_state.time_zone:
            self.lookup_device_timezone(peplink_client)

        tz = ZoneInfo(self.global_state.time_zone)

        month_start = datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=tz
        )
        month_end = month_start + relativedelta(months=1)
        usage = peplink_client.client_bandwidth_usage(
            period="monthly", from_=month_start, to=month_end
        )
        clients = usage["monthly"].get(month_start.date().isoformat(), [])
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
