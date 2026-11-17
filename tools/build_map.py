"""Build assets/samsun_map.json (SVG paths of Samsun's 17 districts + neighbours) from geoBoundaries TUR ADM2.

Source data: geoBoundaries gbOpen TUR ADM2 (derived from OpenStreetMap, ODbL 1.0).
Usage: python tools/build_map.py path/to/geoBoundaries-TUR-ADM2_simplified.geojson
"""
import json
import math
import sys
from pathlib import Path

SAMSUN = ["Alaçam", "Asarcık", "Atakum", "Ayvacık", "Bafra", "Canik", "Çarşamba", "Havza", "İlkadım",
          "Kavak", "Ladik", "19 Mayıs", "Salıpazarı", "Tekkeköy", "Terme", "Vezirköprü", "Yakakent"]
# Our canonical spelling for display.
DISPLAY = {"19 Mayıs": "19 Mayıs"}

VIEW = (34.92, 40.62, 37.32, 41.86)  # lon_min, lat_min, lon_max, lat_max
LAT0 = (VIEW[1] + VIEW[3]) / 2
KX = math.cos(math.radians(LAT0))
WIDTH = 1000.0
SCALE = WIDTH / ((VIEW[2] - VIEW[0]) * KX)
HEIGHT = (VIEW[3] - VIEW[1]) * SCALE
TOL = 0.9  # simplification tolerance in output units


def project(lon, lat):
    return ((lon - VIEW[0]) * KX * SCALE, (VIEW[3] - lat) * SCALE)


def dp(points, tol):
    """Douglas-Peucker simplification."""
    if len(points) < 3:
        return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-9
    best_i, best_d = 0, -1.0
    for i in range(1, len(points) - 1):
        px, py = points[i]
        d = abs(dy * px - dx * py + x2 * y1 - y2 * x1) / norm
        if d > best_d:
            best_i, best_d = i, d
    if best_d > tol:
        left = dp(points[: best_i + 1], tol)
        right = dp(points[best_i:], tol)
        return left[:-1] + right
    return [points[0], points[-1]]


def rings_of(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    return geom["coordinates"]  # MultiPolygon


def ring_area_centroid(pts):
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a *= 0.5
    if abs(a) < 1e-9:
        return 0.0, pts[0][0], pts[0][1]
    return abs(a), cx / (6 * a), cy / (6 * a)


def main(src):
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    out = {"width": round(WIDTH), "height": round(HEIGHT), "districts": {}, "context": [],
           "credit": "Harita verisi © OpenStreetMap katkıcıları (ODbL), geoBoundaries"}
    for f in data["features"]:
        name = f["properties"]["shapeName"]
        polys = rings_of(f["geometry"])
        # quick bbox test against the view
        lons = [p[0] for poly in polys for p in poly[0]]
        lats = [p[1] for poly in polys for p in poly[0]]
        cxl, cyl = (min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2
        in_samsun = name in SAMSUN and 34.9 < cxl < 37.3 and 40.6 < cyl < 41.9
        if not in_samsun and (max(lons) < VIEW[0] or min(lons) > VIEW[2] or max(lats) < VIEW[1] or min(lats) > VIEW[3]):
            continue
        d_parts, best = [], (0.0, 0.0, 0.0)
        for poly in polys:
            for k, ring in enumerate(poly):
                pts = [project(lon, lat) for lon, lat in ring]
                # closed ring: simplify the two halves separately (DP needs distinct endpoints)
                half = len(pts) // 2
                pts = dp(pts[: half + 1], TOL)[:-1] + dp(pts[half:], TOL)
                if len(pts) < 4:
                    continue
                d_parts.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts[:-1]) + "Z")
                if k == 0:
                    area, cx, cy = ring_area_centroid(pts[:-1])
                    if area > best[0]:
                        best = (area, cx, cy)
        d = "".join(d_parts)
        if in_samsun:
            out["districts"][DISPLAY.get(name, name)] = {"d": d, "cx": round(best[1], 1), "cy": round(best[2], 1),
                                                         "area": round(best[0])}
        else:
            out["context"].append(d)
    missing = [n for n in SAMSUN if DISPLAY.get(n, n) not in out["districts"]]
    if missing:
        sys.exit(f"missing districts: {missing}")
    dst = Path(__file__).resolve().parent.parent / "assets" / "samsun_map.json"
    dst.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {dst} ({dst.stat().st_size // 1024} KB), {len(out['districts'])} districts, {len(out['context'])} context shapes")


if __name__ == "__main__":
    main(sys.argv[1])
