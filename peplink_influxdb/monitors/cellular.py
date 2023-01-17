from typing import Generator
import re

from peplink_api.services import PepLinkClientService

from .base import Measurement, Monitor


class CellularMonitor(Monitor):
    refresh_rate: int = 1  # seconds

    def update(self, peplink_client: PepLinkClientService) -> Generator[Measurement, None, None]:
        status = peplink_client.wan_status()
        for id_ in status["order"]:
            data = status[str(id_)]
            if data["type"] != "cellular":
                continue
            network = Measurement(
                "cellular.network",
                {"wan": id_},
                {
                    "technology": data["cellular"]["dataTechnology"],
                    "mcc": int(data["cellular"]["mcc"]),
                    "mnc": int(data["cellular"]["mnc"]),
                },
            )
            signal = Measurement(
                "cellular.signal",
                {"wan": id_},
                {
                    "level": data["cellular"]["signalLevel"],
                },
            )
            for rat in data["cellular"]["rat"]:
                for band in rat["band"]:
                    if data["cellular"]["dataTechnology"] == "LTE":
                        m = re.match(r"^LTE Band (\d+) \((\d+) MHz\)$", band["name"])
                        network.fields["band"] = int(m.group(1))
                        network.fields["frequency"] = int(m.group(2))
                    signal.fields["rsrp"] = band["signal"]["rsrp"]
                    signal.fields["rsrq"] = band["signal"]["rsrq"]
                    signal.fields["rssi"] = band["signal"]["rssi"]
                    signal.fields["sinr"] = band["signal"]["sinr"]
            yield network
            yield signal
