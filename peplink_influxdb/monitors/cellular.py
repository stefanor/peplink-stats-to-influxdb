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
                if sim_data["active"] and "iccid" in sim_data:
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
            network.fields["connected"] = data["statusLed"] == "green"

            signal = Measurement(
                "cellular.signal",
                active_cell_tags,
                {},
            )
            if "signalLevel" in cellular:
                signal.fields["level"] = cellular["signalLevel"]

            signal.fields["connections"] = 0
            for rat in cellular.get("rat", []):
                for band in rat["band"]:
                    if dataTech in ("LTE", "LTE-A", "WCDMA"):
                        m = re.match(r"^(?:LTE|WCDMA) Band (\d+) \((?:\w+ )?(\d+)(?:/\d+)? MHz\)$", band["name"])
                        if m:
                            band_no = int(m.group(1))
                            frequency = int(m.group(2))
                            if "band" in network.fields:
                                band_no = min(network.fields["band"], band_no)
                                frequency = min(network.fields["frequency"], frequency)
                            network.fields["band"] = band_no
                            network.fields["frequency"] = frequency
                        else:
                            log.error("Unknown band: %r", band)
                    metrics = None
                    if "sinr" in band.get("signal", {}):
                        metrics = ("rsrp", "rsrq", "rssi", "sinr")
                    elif "ecio" in band.get("signal", {}):
                        metrics = ("rssi", "ecio", "rscp")
                    else:
                        if "signal" in band:
                            log.error("No sinr/ecio in signal: %r", band["signal"])
                    if metrics:
                        signal.fields["connections"] += 1
                        for metric in metrics:
                            if metric in band["signal"]:
                                value = band["signal"][metric]
                                if metric in signal.fields:
                                    value = max(signal.fields[metric], value)
                                signal.fields[metric] = value
            if network.fields:
                yield network
            if signal.fields:
                yield signal
