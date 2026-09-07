"""Network schema: harbours (nodes) and routes (edges).

The network is a flexible directed graph, not a set of fixed round-trips. Multi-leg
itineraries / services (A->B->C->A) are deliberately *not* modelled here — they
belong to the scheduling layer later.

Conventions
-----------
- Coordinates are stored as named ``lat`` / ``lon`` fields everywhere in-process.
  GeoJSON's ``(lon, lat)`` ordering is converted at the IO boundary (``io/routes.py``).
- A route ``path`` is the actually-sailed polyline, ordered origin -> destination.
  Segment-by-segment physics needs the real path, so a great-circle line is not
  assumed or generated.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from waterpath.geo import haversine_km

#: A route's first/last path vertex must lie within this distance of its
#: origin/destination harbour, otherwise the network is rejected.
PATH_ENDPOINT_TOLERANCE_KM = 2.0


class Point(BaseModel):
    """A geographic position."""

    model_config = {"frozen": True}

    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)


class Harbour(BaseModel):
    """A network node where vessels call."""

    model_config = {"frozen": True}

    harbour_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    #: ISO 3166-1 alpha-2 code, used later to resolve the public-holiday calendar.
    country_code: str | None = None

    @field_validator("country_code")
    @classmethod
    def _normalise_country_code(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError("country_code must be an ISO 3166-1 alpha-2 code (e.g. 'IE')")
        return v

    @property
    def point(self) -> Point:
        return Point(lat=self.lat, lon=self.lon)


class Route(BaseModel):
    """A directed edge between two harbours, with its sailed path."""

    model_config = {"frozen": True}

    route_id: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    #: Ordered polyline from origin to destination (>= 2 vertices).
    path: tuple[Point, ...] = Field(min_length=2)
    name: str | None = None
    #: Per-route override for the number of physics segments; ``None`` -> use the
    #: global config default.
    n_segments: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _endpoints_distinct(self) -> Route:
        if self.origin == self.destination:
            raise ValueError(
                f"route {self.route_id!r}: origin and destination are the same harbour "
                f"({self.origin!r})"
            )
        return self

    @property
    def start(self) -> Point:
        return self.path[0]

    @property
    def end(self) -> Point:
        return self.path[-1]


class Network(BaseModel):
    """Validated collection of harbours and routes."""

    model_config = {"frozen": True}

    harbours: tuple[Harbour, ...] = Field(min_length=1)
    routes: tuple[Route, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _cross_check(self) -> Network:
        h_ids: set[str] = set()
        for h in self.harbours:
            if h.harbour_id in h_ids:
                raise ValueError(f"duplicate harbour_id {h.harbour_id!r}")
            h_ids.add(h.harbour_id)

        r_ids: set[str] = set()
        by_id = {h.harbour_id: h for h in self.harbours}
        for r in self.routes:
            if r.route_id in r_ids:
                raise ValueError(f"duplicate route_id {r.route_id!r}")
            r_ids.add(r.route_id)

            for role, hid, vertex in (
                ("origin", r.origin, r.start),
                ("destination", r.destination, r.end),
            ):
                harbour = by_id.get(hid)
                if harbour is None:
                    raise ValueError(
                        f"route {r.route_id!r}: {role} {hid!r} is not a known harbour"
                    )
                gap = haversine_km(harbour.lat, harbour.lon, vertex.lat, vertex.lon)
                if gap > PATH_ENDPOINT_TOLERANCE_KM:
                    raise ValueError(
                        f"route {r.route_id!r}: path {role} is {gap:.1f} km from harbour "
                        f"{hid!r} (tolerance {PATH_ENDPOINT_TOLERANCE_KM} km)"
                    )
        return self

    def harbour(self, harbour_id: str) -> Harbour:
        for h in self.harbours:
            if h.harbour_id == harbour_id:
                return h
        raise KeyError(f"no harbour {harbour_id!r}")

    def route(self, route_id: str) -> Route:
        for r in self.routes:
            if r.route_id == route_id:
                return r
        raise KeyError(f"no route {route_id!r}")
