from typing import Generator

from peplink_api.services import PepLinkClientService

from .base import Measurement, Monitor


class WANTrafficMonitor(Monitor):
    refresh_rate: int = 1  # seconds

    def update(self, peplink_client: PepLinkClientService) -> Generator[Measurement, None, None]:
        stats = peplink_client.traffic_status()
        assert stats["bandwidth"]["unit"] == "kbps"
        for id_ in stats["bandwidth"]["order"]:
            wan_stats = stats["bandwidth"][str(id_)]
            yield Measurement("wan.speed", {"wan": id_}, wan_stats["overall"])

        assert stats["lifetime"]["unit"] == "MB"
        yield Measurement("wan.lifetime_usage", {}, stats["lifetime"]["all"]["overall"])

        assert stats["traffic"]["unit"] == "MB"
        for id_ in stats["traffic"]["order"]:
            wan_stats = stats["traffic"][str(id_)]
            yield Measurement("wan.usage", {"wan": id_}, wan_stats["overall"])
