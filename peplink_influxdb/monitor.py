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
        self.hostname_cache = {}

    def run_forever(self):
        while True:
            self.run_once(log_errors=True)
            self.sleep()

    def sleep(self):
        time.sleep(self.interval)

    def run_once(self, log_errors=False):
        if not self.hostname_cache:
            self.seed_hostname_cache()

        points = []
        for iterator in (self.get_cell_stats, self.get_client_stats,
                         self.get_global_traffic_stats):
            try:
                for statistic in iterator():
                    points.append(statistic._asdict())
            except:
                if not log_errors:
                    raise
                log.exception("Error")
        self.influx.write_points(points)


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

    def seed_hostname_cache(self):
        clients = self.peplink.client_status(weight="lite")["list"]
        for client in clients:
            self.hostname_cache[client["mac"]] = client["name"]

    def get_client_stats(self):
        clients = self.peplink.client_status(weight="full", active_only=True)["list"]
        for client in clients:
            self.hostname_cache[client["mac"]] = client["name"]
            if client["active"]:
                if client.get("connectionType") == "wireless":
                    yield Measurement(
                        "client.signal",
                        {
                            "ip": client["ip"],
                            "mac": client["mac"],
                            "name": client["name"],
                        },
                        client["signal"],
                    )

                assert client["speed"]["unit"] == "kbps"
                yield Measurement(
                    "client.speed",
                    {
                        "ip": client["ip"],
                        "mac": client["mac"],
                        "name": client["name"],
                    },
                    {
                        "upload": client["speed"]["upload"],
                        "download": client["speed"]["download"],
                    },
                )

        month_start = datetime.datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        usage = self.peplink.client_bandwidth_usage(period="monthly", from_=month_start)
        clients = usage["monthly"][month_start.date().isoformat()]
        for client in clients:
            tags = {"ip": client["ip"], "mac": client["mac"]}
            hostname = self.hostname_cache.get(client["mac"])
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

    def get_global_traffic_stats(self):
        stats = self.peplink.traffic_status()
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
