from datetime import datetime
from enum import Enum
from typing import Union
from .api_stops import Point
from .base import Response, _do_request, _parse_time

_ENDPOINT = "/dm"


class TransportationType(Enum):
    """Represents means of transportation

    For departures do not use the 'by foot` types like stairway and footpath!
    """

    BUS = "Bus"
    TRAM = "Tram"
    TRAIN = "Train"
    FERRY = "Ferry"
    CITY_BUS = "CityBus"
    PLUS_BUS = "PlusBus"
    CLOCK_BUS = "ClockBus"
    """Looks like something from RVSOE, like line 'N'"""
    CABLEWAY = "Cableway"
    INTERCITY_BUS = "IntercityBus"
    SUBURBAN_RAILWAY = "SuburbanRailway"
    HAILED_SHARED_TAXI = "HailedSharedTaxi"

    RAPID_TRANSIT = "RapidTransit"
    """RE 'ReginalExpress'"""

    FOOTPATH = "Footpath"
    STAIRWAY_UP = "MobilityStairsUp"
    STAIRWAY_DOWN = "MobilityStairsDown"
    RAMP_UP = "MobilityRampUp"
    RAMP_DOWN = "MobilityRampDown"


class Punctuality(Enum):
    IN_TIME = "InTime"
    DELAYED = "Delayed"


class Departure:
    id: str
    """ID of the departure"""
    vehicle: TransportationType
    """Vehicle of this departure"""
    line_name: str
    """Line name / number as string"""
    direction: str
    """Direction of line"""
    state: Punctuality
    """State of the departure"""
    scheduled: datetime
    """Time this departed was scheduled for"""
    real_time: datetime = None
    """The real time departure (differs if delayed)"""
    departure: int
    """Departure in seconds from now"""

    def __init__(self, data: dict):
        self.id = data.pop("Id")
        self.vehicle = TransportationType(data.pop("Mot"))
        self.line_name = data.pop("LineName")
        self.direction = data.pop("Direction")
        self.state = Punctuality(data.pop("State", "InTime"))
        self.scheduled = _parse_time(data.pop("ScheduledTime"))
        if "RealTime" in data:
            self.real_time = _parse_time(data.pop("RealTime"))
        else:
            self.real_time = None
        # other data: Diva -> Number + Network
        # RouteChanges [int]
        # Platform: Name + Type

    @property
    def delay(self):
        if self.real_time:
            return int((self.real_time - self.scheduled).total_seconds())
        return 0

    @property
    def departure(self):
        return int((self.scheduled - datetime.now()).total_seconds() + self.delay)


class DepartureResponse(Response):
    name: str
    """Name of the stop"""
    place: str
    """City of this stop"""
    departures: list[Departure]
    """List of departures"""
    more: bool
    """True if more results can queried"""

    def __init__(self, data: dict, parameters: dict):
        super().__init__(data, parameters)
        self.name = data["Name"]
        self.place = data["Place"]
        self.departures = []
        dd = {}
        self.more = "limit" in parameters and parameters["limit"] == len(data["Departures"])
        # Filter out duplicates
        for d in data["Departures"]:
            dep = Departure(d)
            dd[(dep.id, dep.scheduled)] = dep
        self.departures = list(dd.values())


def get_departures(stopid: Union[Point, int], **kwargs) -> DepartureResponse:
    """Get departues on given stop

    Parameters:
        limit (int): Maximum number of results
        time (datetime, str): Starting of departures
        isarrival (bool): Is the time specified above supposed to be interpreted as arrival or departure time
        shorttermchanges (bool): Include changes
        vehicle (list[Vehicle]): Allowed modes of transport
    """
    if isinstance(stopid, Point):
        if not stopid.is_stop:
            raise TypeError("Departures can only queried for stop.")
        stopid = stopid.id

    if "vehicle" in kwargs:
        for idx, v in enumerate(kwargs["vehicle"]):
            if isinstance(v, TransportationType):
                kwargs["vehicle"][idx] = v.value
        kwargs["mot"] = kwargs["vehicle"]
        del kwargs["vehicle"]

    if "time" in kwargs and isinstance(kwargs["time"], datetime):
        kwargs["time"] = kwargs["time"].isoformat()

    return _do_request(_ENDPOINT, {"stopid": stopid, **kwargs}, DepartureResponse)
