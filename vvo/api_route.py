from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union
from RacingTeam.api.api_departure import Punctuality, TransportationType

from RacingTeam.api.api_stops import Point
from RacingTeam.api.base import Response, _do_request, _parse_time


_ENDPOINT = "/tr/trips"


@dataclass
class Vehicle:
    """Vehicle used for a route"""

    type: TransportationType
    """Vehicle type"""
    direction: Optional[str]
    """Direction of line / target destination
    
    Always set, except for `TransportationType.FOOTPATH`
    """
    name: Optional[str]
    """name or number of line
    
    Always set, except for `TransportationType.FOOTPATH`
    """
    changes: list[str]
    """list of current line changes"""

    @staticmethod
    def from_data(data: dict):
        """Create vehicle instance from API data

        Example:
         {
          "DlId": "de:vvo:21-62",
          "Type": "Bus",
          "Name": "62",
          "Direction": "Johannstadt",
          "Changes": [
            "13599",
            "12906"
          ],
          "Diva": {
            "Number": "21062",
            "Network": "voe"
          }
        """
        return Vehicle(
            type=TransportationType(data["Type"]),
            direction=data.get("Direction", None),
            name=data.get("Name", None),
            changes=data.get("Changes", []),
        )


@dataclass
class RouteStop:
    """Represents a regular stop on a route"""

    @dataclass
    class Platform:
        """Represents a platform where a vehicle stops"""

        name: str
        type: str

    name: str
    """Name of the stop"""
    place: str
    """Place of the stop, meaning the city or community"""
    point_id: int
    """ID of this stop, see `Point`"""
    type: str
    """Type of this stop (always 'Stop'?)"""
    arrival_scheduled: datetime
    """Scheduled arrival time"""
    arrival_realtime: Optional[datetime]
    """Current realtime arrival time"""
    arrival_state: Optional[Punctuality]
    """Punctuality of the arrival"""
    departure_scheduled: datetime
    """Scheduled departure time"""
    departure_realtime: Optional[datetime]
    """Current realtime departure time"""
    departure_state: Optional[Punctuality]
    """Punctuality of the departure"""
    platform: Optional[Platform]
    """Platform where the vehicle stops"""

    latitude_gk4: int
    longitude_gk4: int

    @property
    def location(self):
        """Coordinates in WGS84 (longitude, latitude)"""
        from .coordinates_utils import from_gk4

        return from_gk4(self.latitude_gk4, self.longitude_gk4)

    @property
    def arrival(self):
        """Arrival time

        Shortcut for `RouteStop.arrival_realtime if RouteStop.arrival_realtime else RoutStop.arrival_scheduled`
        """
        return self.arrival_realtime or self.arrival_scheduled

    @property
    def departure(self):
        """Departure time

        Shortcut for `RouteStop.departure_realtime if RouteStop.departure_realtime else RoutStop.departure_scheduled`
        """
        return self.departure_realtime or self.departure_scheduled

    @staticmethod
    def from_data(data: dict):
        """Create instance from API data

        Example:
        {
            "ArrivalTime": "/Date(1644164100000-0000)/",
            "DepartureTime": "/Date(1644164100000-0000)/",
            "ArrivalRealTime": "/Date(1644164100000-0000)/",
            "DepartureRealTime": "/Date(1644164100000-0000)/",
            "Place": "Dresden",
            "Name": "St.-Benno-Gymnasium",
            "Type": "Stop",
            "DataId": "33000080",
            "DhId": "de:14612:80",
            "Platform": {
            "Name": "2",
            "Type": "Platform"
            },
            "Latitude": 5658653,
            "Longitude": 4623295,
            "DepartureState": "InTime",
            "ArrivalState": "InTime",
            "CancelReasons": []
        }"""
        return RouteStop(
            name=data["Name"],
            place=data["Place"],
            point_id=int(data["DataId"]),
            type=data["Type"],
            arrival_scheduled=_parse_time(data["ArrivalTime"]),
            arrival_state=Punctuality(data["ArrivalState"]) if "ArrivalState" in data else None,
            arrival_realtime=_parse_time(data["ArrivalRealTime"]) if "ArrivalRealTime" in data else None,
            departure_scheduled=_parse_time(data["DepartureTime"]),
            departure_state=Punctuality(data["DepartureState"]) if "DepartureState" in data else None,
            departure_realtime=_parse_time(data["DepartureRealTime"]) if "DepartureRealTime" in data else None,
            platform=RouteStop.Platform(data["Platform"]["Name"], data["Platform"]["Type"])
            if "Platform" in data
            else None,
            latitude_gk4=data["Latitude"],
            longitude_gk4=data["Longitude"],
        )


@dataclass
class PartialRoute:
    id: Optional[int]
    """Internal API id of this subroute"""
    duration: Optional[int]
    """Duration of this subroute in minutes"""
    vehicle: Vehicle
    """Vehicle used for this subroute"""
    stops: list[RouteStop]
    """Regular stops on this subroute"""
    next_departures: list[datetime]
    """Next departures of this subroute"""
    previous_departures: list[datetime]
    """Previous departures of this subroute"""

    @staticmethod
    def from_data(data: dict):
        """Create instance from API data"""
        partial = PartialRoute(
            id=data.get("PartialRouteId", None),
            duration=data.get("Duration", None),
            vehicle=Vehicle.from_data(data["Mot"]),
            stops=[RouteStop.from_data(d) for d in data.get("RegularStops", [])],
            next_departures=[_parse_time(td) for td in data.get("NextDepartureTimes", [])],
            previous_departures=[_parse_time(td) for td in data.get("PreviousDepartureTimes", [])],
        )
        if partial.duration is None and len(partial.stops) > 0:
            partial.duration = round((partial.stops[-1].arrival - partial.stops[0].departure).total_seconds / 60)
        return partial


class Route:
    duration: int
    """Duration in minutes"""
    interchanges: int
    """Number of interchanges on the route"""
    partial_routes: list[PartialRoute]
    """Partial routes of this route, subsections of the route with different lines"""
    vehicles: list[Vehicle]
    """Chain of vehicles used for this route"""

    def __init__(self, data: dict):
        self.duration = data["Duration"]
        self.interchanges = data["Interchanges"]
        self.partial_routes = [PartialRoute.from_data(d) for d in data["PartialRoutes"]]
        self.vehicles = [Vehicle.from_data(d) for d in data["MotChain"]]


class RouteResponse(Response):
    routes: list[Route]

    def __init__(self, data: dict, parameters: dict):
        super().__init__(data, parameters)
        if self.ok:
            self.routes = [Route(d) for d in data["Routes"]]
        else:
            self.routes = []


def find_routes(start: Union[Point, int], destination: Union[Point, int], **kwargs) -> RouteResponse:
    """Get departues on given stop

    Parameters:
        limit (int): Maximum number of results
        time (datetime, str): Starting of departures / end of arrival
        isarrivaltime (bool): Is the time specified above supposed to be interpreted as arrival or departure time
        shorttermchanges (bool): Include changes
        vehicle (list[TransportationType]): Allowed modes of transport
        max_changes (int): Maximum number of changes
    """
    if isinstance(start, Point):
        start = start.id
    if isinstance(destination, Point):
        destination = destination.id

    settings = {"maxChanges": kwargs.pop("max_changes", "Unlimited")}
    if "vehicle" in kwargs:
        for idx, v in enumerate(kwargs["vehicle"]):
            if isinstance(v, TransportationType):
                kwargs["vehicle"][idx] = v.value
        settings["mot"] = kwargs.pop("vehicle")

    if "time" in kwargs and isinstance(kwargs["time"], datetime):
        kwargs["time"] = kwargs["time"].isoformat()

    return _do_request(
        _ENDPOINT,
        {"origin": start, "destination": destination, "standardSettings": settings, **kwargs},
        RouteResponse,
    )
