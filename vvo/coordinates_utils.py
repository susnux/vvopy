from pyproj import Proj

# EPSG:5678
projection = Proj(
    "+proj=tmerc +lat_0=0 +lon_0=12 +k=1 +x_0=4500000 +y_0=0 +ellps=bessel +towgs84=598.1,73.7,418.2,0.202,0.045,-2.455,6.7 +units=m +no_defs"
)


def to_gk4(lon, lat):
    return projection(lon, lat)


def from_gk4(right, up):
    return projection(up, right, inverse=True)
