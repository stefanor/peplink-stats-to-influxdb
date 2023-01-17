from collections import namedtuple
from typing import Generator, Union

from peplink_api.services import PepLinkClientService


Measurement = namedtuple("Measurement", ["measurement", "tags", "fields"])


class GlobalState:
    # For monitors to share state
    # TODO: refactor into a pub/sub mechanism
    hostname_cache: dict[str, str] = {}  # mac: name
    active_cell_tags: dict[
        int, dict[str, Union[int, str]]
    ] = {}  # WAN id: {iccid, mcc, mnc, carrier}


class Monitor:
    refresh_rate: int = 1  # seconds
    last_ran: float = 0.0  # timestamp

    def __init__(self, global_state: GlobalState) -> None:
        self.global_state = global_state

    def update(
        self, peplink_client: PepLinkClientService
    ) -> Generator[Measurement, None, None]:
        raise NotImplementedError("update() needs to be provided")
