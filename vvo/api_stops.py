from typing import Union
from .coordinates_utils import to_gk4, from_gk4
from .base import Response, _do_request


class Point:
    def __init__(self, data: str) -> None:
        self.data = data
        (
            self.id,
            self.type,
            self.place,
            self.name,
            self.gk4_right,
            self.gk4_up,
            self.distance,
            self._,
            self.shortcut,
        ) = data.split("|")
        if self.is_stop:
            self.id = int(self.id)
        if self.distance:
            self.distance = int(self.distance)
        self.gk4_right = int(self.gk4_right)
        self.gk4_up = int(self.gk4_up)

    @property
    def location(self):
        """Location as longitude latitude"""
        return from_gk4(self.gk4_right, self.gk4_up)

    @property
    def is_coord(self):
        """If this point is a coordinate"""
        return self.type == "c"

    @property
    def is_stop(self):
        """If this point is a stop"""
        return self.type == "" and (isinstance(self.id, int) or (isinstance(self.id, str) and self.id.isnumeric))

    def __repr__(self) -> str:
        return f"Point({self.data})"


class PointResponse(Response):
    points = []

    def __init__(self, data, parameters):
        super().__init__(data, parameters)
        self.ok = self.status and data["PointStatus"] != "NotIdentified"
        if self.ok:
            self.points = [Point(p) for p in data["Points"]]


def find_points(
    query: Union[str, int] = None,
    location: tuple[float, float] = None,
    limit: int = None,
    only_stops=False,
    regional=False,
    shortcuts=False,
    assigned_stops=False,
):
    """Find stops by query, location, or ID
    Args:
            query: String query of stop name or stop id
            location: Tuple of longitude and latitude
            limit: Limit of stops to query
            regional: Only include regional stops (string query only)
            only_stops: If only stops should be returned
            assigned_stops: Include stops assigned to coordinates (location only)
                        shortcuts: Include shortcuts of stops
    """
    json = {
        "limit": limit,
        "stopsOnly": only_stops,
        "regionalOnly": regional,
        "stopShortcuts": shortcuts,
    }
    if location:
        gk4 = to_gk4(*location)
        json.update({"query": f"coord:{round(gk4[0])}:{round(gk4[1])}", "assignedstops": assigned_stops})
    else:
        json.update({"query": query})

    return _do_request("tr/pointfinder", json, PointResponse)


def find_stops(query, regional=True, shortcuts=False, limit: int = None) -> PointResponse:
    if isinstance(query, (str, int)):
        return find_points(query=query, limit=limit, shortcuts=shortcuts, regional=regional, only_stops=True)
    elif isinstance(query, tuple) and len(query) == 2:
        return find_points(
            location=query,
            regional=regional,
            shortcuts=shortcuts,
            assigned_stops=True,
            limit=limit,
            only_stops=True,
        )
    else:
        raise ValueError
