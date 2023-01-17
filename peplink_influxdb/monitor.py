import datetime
import logging
import re
import time
from collections import namedtuple
from itertools import chain

Measurement = namedtuple("Measurement", ["measurement", "tags", "fields"])


log = logging.getLogger(__name__)


class Monitor:
    def __init__(self, influx_client, peplink_client, interval):
        self.influx = influx_client
        self.peplink = peplink_client
        self.interval = interval

    def run_forever(self):
        while True:
            try:
                self.run_once()
            except:
                log.exception("Error")
            self.sleep()

    def sleep(self):
        time.sleep(self.interval)

    def run_once(self):
        self.record_stats(chain(self.get_cell_stats(), self.get_client_stats()))

    def record_stats(self, stats):
        self.influx.write_points([stat._asdict() for stat in stats])

    def get_cell_stats(self):
        status = self.peplink.wan_status()
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

    def get_client_stats(self):
        clients = self.peplink.client_status(weight="full", active_only=True)["list"]
        for client in clients:
            if client["connectionType"] == "wireless" and client["active"]:
                yield Measurement(
                    "client.signal",
                    {
                        "ip": client["ip"],
                        "mac": client["mac"],
                        "name": client["name"],
                    },
                    client["signal"],
                )

        month_start = datetime.datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        usage = self.peplink.client_bandwidth_usage(period="monthly", from_=month_start)
        clients = usage["monthly"][month_start.date().isoformat()]
        for client in clients:
            yield Measurement(
                "client.usage",
                {"ip": client["ip"]},
                {
                    "upload": client["upload"],
                    "download": client["download"],
                },
            )
