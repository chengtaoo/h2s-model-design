"""Generate a real 20 x 30 x 40 mm STL and projected SVG, no printer required."""
import argparse
import json
from pathlib import Path
import trimesh


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('work/demo'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    mesh = trimesh.creation.box(extents=[20, 30, 40])
    mesh.apply_translation([10, 15, 20])
    mesh.export(args.output / 'demo.stl')
    # Project actual mesh triangles; a geometric preview, not a generated image.
    polygons = []
    faces = sorted(mesh.triangles, key=lambda tri: float(tri.mean(axis=0).sum()))
    for tri in faces:
        points = ' '.join(f'{180 + 5*(x-y):.2f},{340 - 5*z - 2*(x+y):.2f}' for x, y, z in tri)
        polygons.append(f'<polygon points="{points}" fill="#7ab8ec" fill-opacity="0.65" stroke="#244661"/>')
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400"><rect width="400" height="400" fill="white"/>'
    svg += ''.join(polygons) + '<text x="20" y="385" font-size="16">20 x 30 x 40 mm — geometry demo</text></svg>'
    (args.output / 'preview.svg').write_text(svg, encoding='utf-8')
    (args.output / 'design-spec.json').write_text(json.dumps({'name': 'demo', 'units': 'mm', 'dimensions_mm': [20,30,40], 'status': 'geometry_only'}, indent=2), encoding='utf-8')
    print('Created demo.stl, preview.svg, design-spec.json. This is not a Bambu project or slicing test.')


if __name__ == '__main__':
    main()
