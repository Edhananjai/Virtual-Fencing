def point_in_polygon(lat: float, lon: float, polygon: list[list[float]]) -> bool:
    """
    Ray-casting algorithm to check if a point (lat, lon) is inside a polygon.
    polygon: list of [lat, lon] vertices.
    Returns True if inside, False if outside.
    """
    n = len(polygon)
    if n < 3:
        return False

    inside = False
    j = n - 1

    for i in range(n):
        yi, xi = polygon[i]
        yj, xj = polygon[j]

        if ((yi > lon) != (yj > lon)) and (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi):
            inside = not inside

        j = i

    return inside
