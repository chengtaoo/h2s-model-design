"""Read-only STL QA. Input coordinates must already be millimetres."""
import argparse
import json
from pathlib import Path
import sys


def inspect(path):
    import numpy as np
    import trimesh
    mesh = trimesh.load_mesh(path, process=False)
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
        raise ValueError('Expected a non-empty triangle mesh')
    if not np.isfinite(mesh.vertices).all():
        raise ValueError('Mesh has non-finite coordinates')
    # STL repeats vertex coordinates. Weld identical positions for topology
    # analysis only; never write this normalized mesh over the input.
    mesh.merge_vertices(digits_vertex=9)
    extents = mesh.extents
    checks = {
        'nondegenerate_faces': bool((mesh.area_faces > 1e-12).all()),
        'watertight': bool(mesh.is_watertight),
        'consistent_winding': bool(mesh.is_winding_consistent),
        'positive_volume': bool(mesh.volume > 0),
        'within_nominal_h2s_volume_current_orientation': bool((extents <= [340, 320, 340]).all()),
    }
    # Count face components using shared vertices without optional scipy/networkx.
    parent = list(range(len(mesh.vertices)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b, c in mesh.faces:
        anchor = find(int(a))
        parent[find(int(b))] = anchor
        parent[find(int(c))] = anchor
    components = len({find(int(v)) for v in mesh.faces.reshape(-1)})
    return {
        'input': str(Path(path).resolve()), 'assumed_units': 'mm',
        'bounds_mm': mesh.bounds.tolist(), 'dimensions_mm': extents.tolist(),
        'faces': len(mesh.faces), 'volume_mm3': float(mesh.volume),
        'vertex_connected_components': components,
        'checks': checks, 'basic_checks_pass': all(checks.values()),
        'not_checked': ['self_intersections', 'minimum_wall_thickness', 'support_requirements',
                        'assembly_fit', 'strength', 'plate_exclusions', 'slicing'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mesh')
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    try:
        report = inspect(args.mesh)
        code = 0 if report['basic_checks_pass'] else 2
    except Exception as exc:
        report = {'basic_checks_pass': False, 'error': str(exc)}
        code = 1
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
