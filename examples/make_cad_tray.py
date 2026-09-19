"""Parameterized open tray: CAD source -> STEP/STL and actual geometry SVG."""
import argparse
import json
from pathlib import Path
import cadquery as cq


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--length', type=float, default=100)
    parser.add_argument('--width', type=float, default=70)
    parser.add_argument('--height', type=float, default=30)
    parser.add_argument('--wall', type=float, default=2)
    parser.add_argument('--output', type=Path, default=Path('work/cad-tray'))
    args = parser.parse_args()
    if not (args.wall > 0 and args.length > 2*args.wall and args.width > 2*args.wall and args.height > args.wall):
        parser.error('Dimensions must leave positive inner space and bottom thickness')
    outer = cq.Workplane('XY').box(args.length, args.width, args.height, centered=(True,True,False))
    # Cavity extends above the tray so the top is genuinely open.
    cavity = cq.Workplane('XY').workplane(offset=args.wall).box(
        args.length-2*args.wall, args.width-2*args.wall, args.height,
        centered=(True,True,False))
    model = outer.cut(cavity)
    assert model.val().isValid()
    args.output.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(model, str(args.output / 'tray.step'))
    cq.exporters.export(model, str(args.output / 'tray.stl'))
    cq.exporters.export(model, str(args.output / 'preview.svg'), exportType='SVG')
    spec = {'name':'tray', 'units':'mm', 'dimensions_mm':[args.length,args.width,args.height],
            'parameters':{'wall':args.wall}, 'status':'geometry_only',
            'assumptions':['Uncolored geometry; assign filament and H2S preset in Studio']}
    (args.output / 'design-spec.json').write_text(json.dumps(spec, indent=2), encoding='utf-8')
    print('CAD tray generated. Import tray.stl into Studio; H2S project/slicing still require Studio.')


if __name__ == '__main__':
    main()
