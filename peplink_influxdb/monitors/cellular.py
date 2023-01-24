from typing import Generator
import logging
import re

from peplink_api.services import PepLinkClientService

from .base import Measurement, Monitor

log = logging.getLogger(__name__)


class CellularMonitor(Monitor):
    refresh_rate: int = 1  # seconds

    def update(
        self, peplink_client: PepLinkClientService
    ) -> Generator[Measurement, None, None]:
        status = peplink_client.wan_status()
        for id_ in status["order"]:
            data = status[str(id_)]
            if data["type"] != "cellular":
                continue
            cellular = data["cellular"]
            iccid = None

            for sim in cellular["sim"]["order"]:
                sim_data = cellular["sim"][str(sim)]
                if sim_data["active"]:
                    iccid = sim_data["iccid"]

            active_cell_tags = {
                "iccid": iccid,
                "wan": id_,
            }
            self.global_state.active_cell_tags[id_] = active_cell_tags

            if "mcc" not in cellular:  # Not Connected
                continue

            active_cell_tags["mcc"] = int(cellular["mcc"])
            active_cell_tags["mnc"] = int(cellular["mnc"])
            active_cell_tags["carrier"] = cellular["carrier"]["name"]

            network = Measurement(
                "cellular.network",
                active_cell_tags,
                {},
            )
            dataTech = cellular.get("dataTechnology")
            if dataTech:
                network.fields["technology"] = dataTech
            generation = {
                "5G": 5.0,  # Guess
                "LTE-A": 4.5,  # Seen
                "LTE": 4.0,  # Seen
                "HSPA": 3.5,  # Guess
                "UMTS": 3.0,  # Guess
                "EGPRS": 2.5,  # Guess
                "GPRS": 2.0,  # Guess
            }.get(dataTech)
            if generation is None:
                if dataTech is not None:
                    log.error("Unknown dataTechnology: %s", dataTech)
            else:
                network.fields["generation"] = generation

            signal = Measurement(
                "cellular.signal",
                active_cell_tags,
                {},
            )
            if "signalLevel" in cellular:
                signal.fields["level"] = cellular["signalLevel"]

            for rat in cellular.get("rat", []):
                for band in rat["band"]:
                    if dataTech in ("LTE", "LTE-A"):
                        m = re.match(r"^LTE Band (\d+) \((\d+) MHz\)$", band["name"])
                        if m:
                            network.fields["band"] = int(m.group(1))
                            network.fields["frequency"] = int(m.group(2))
                        else:
                            log.error("Unknown band: %r", band)
                    if "rsrp" in band["signal"]:
                        signal.fields["rsrp"] = band["signal"]["rsrp"]
                        signal.fields["rsrq"] = band["signal"]["rsrq"]
                        signal.fields["rssi"] = band["signal"]["rssi"]
                        signal.fields["sinr"] = band["signal"]["sinr"]
                        break  # For now, we only report the first LTE band
                    else:
                        log.error("No rsrp in signal: %r", band["signal"])
            yield network
            yield signal
