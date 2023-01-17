from typing import Generator

from peplink_api.services import PepLinkClientService

from .base import Measurement, Monitor


class WANTrafficMonitor(Monitor):
    refresh_rate: int = 1  # seconds

    def update(self, peplink_client: PepLinkClientService) -> Generator[Measurement, None, None]:
        stats = peplink_client.traffic_status()
        assert stats["lifetime"]["unit"] == "MB"
        yield Measurement("wan.lifetime_usage", {}, stats["lifetime"]["all"]["overall"])

        assert stats["bandwidth"]["unit"] == "kbps"
        for id_ in stats["bandwidth"]["order"]:
            wan_stats = stats["bandwidth"][str(id_)]
            tags = {"wan": id_}
            if id_ in self.global_state.active_sim:
                tags["iccid"] = self.global_state.active_sim[id_]
            yield Measurement("wan.speed", tags, wan_stats["overall"])

        assert stats["traffic"]["unit"] == "MB"
        for id_ in stats["traffic"]["order"]:
            wan_stats = stats["traffic"][str(id_)]
            tags = {"wan": id_}
            if id_ in self.global_state.active_sim:
                tags["iccid"] = self.global_state.active_sim[id_]
            yield Measurement("wan.usage", tags, wan_stats["overall"])
