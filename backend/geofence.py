def point_in_polygon(lat: float, lon: float, polygon: list[list[float]]) -> bool:
    """
    Ray-casting algorithm to check if a point (lat, lon) is inside a polygon.
    polygon: list of [lat, lon] vertices.
    Returns True if inside, False if outside.

    Coordinate convention: lat = Y axis, lon = X axis.
    """
    n = len(polygon)
    if n < 3:
        return False

    # Point to test: py = lat, px = lon
    py, px = lat, lon
    inside = False
    j = n - 1

    for i in range(n):
        # Each vertex: [lat, lon] → [y, x]
        iy, ix = polygon[i]
        jy, jx = polygon[j]

        if ((iy > py) != (jy > py)) and (px < (jx - ix) * (py - iy) / (jy - iy) + ix):
            inside = not inside

        j = i

    return inside
