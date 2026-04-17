def parse_bbox_string(bbox_str: str) -> tuple[float, float, float, float]:
    values = [float(value.strip()) for value in bbox_str.split(",")]
    if len(values) != 4:
        raise ValueError("bbox must be minx,miny,maxx,maxy in EPSG:3346")
    return tuple(values)
