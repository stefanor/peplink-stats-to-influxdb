import logging
import time

from .monitors.base import GlobalState
from .monitors.cellular import CellularMonitor
from .monitors.lan_client_usage import LANClientUsageMonitor
from .monitors.lan_client import LanClientMonitor
from .monitors.wan_traffic import WANTrafficMonitor


log = logging.getLogger(__name__)


class Monitor:
    def __init__(self, influx_client, peplink_client, interval):
        self.influx = influx_client
        self.peplink = peplink_client
        self.interval = interval
        self.hostname_cache = {}
        self.monitors = []
        self.global_state = GlobalState()
        for monitor in [
            CellularMonitor,
            LanClientMonitor,
            LANClientUsageMonitor,
            WANTrafficMonitor,
        ]:
            self.monitors.append(monitor(self.global_state))

    def run_forever(self):
        while True:
            self.run_once(log_errors=True)
            self.sleep()

    def sleep(self):
        time.sleep(self.interval)

    def run_once(self, log_errors=False):
        points = []
        for monitor in self.monitors:
            if monitor.last_ran + monitor.refresh_rate > time.time():
                continue
            try:
                for statistic in monitor.update(self.peplink):
                    points.append(statistic._asdict())
            except:
                if not log_errors:
                    raise
                log.exception("Error")
            monitor.last_ran = time.time()
        self.influx.write_points(points)
