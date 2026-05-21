import json, os, sys

WORKDIR = r'D:\Roco_Navigation_Tool_Workspace'

try:
    # --- Load web_data.txt ---
    with open(os.path.join(WORKDIR, 'web_data.txt'), 'rb') as f:
        raw = f.read()
    data = json.loads(raw)

    print(f'[STEP1] JSON loaded. code={data.get("code")}', flush=True)
    d = data['data']
    areas = d.get('areas', [])
    regions = d.get('regions', [])
    types = d.get('types', [])
    type_groups = d.get('type_groups', [])
    print(f'        areas={len(areas)} regions={len(regions)} types={len(types)} type_groups={len(type_groups)}', flush=True)

    # --- Coordinate transform ---
    LNG_MIN, LNG_MAX = -1.237324, 1.205059
    LAT_MIN, LAT_MAX = -0.681458, 0.979792

    def lnglat_to_pixel(lng, lat):
        px = int((lng - LNG_MIN) / (LNG_MAX - LNG_MIN) * 4096)
        py = int((1.0 - (lat - LAT_MIN) / (LAT_MAX - LAT_MIN)) * 4096)
        return px, py

    # --- Process areas ---
    areas_out = []
    for a in areas:
        px, py = lnglat_to_pixel(a.get('lng', 0), a.get('lat', 0))
        areas_out.append({
            'id': a.get('id'),
            'title': a.get('title', ''),
            'pixel_x': px,
            'pixel_y': py,
            'lng': a.get('lng'),
            'lat': a.get('lat')
        })
    print(f'[STEP2] areas processed: {len(areas_out)}', flush=True)

    # --- Process regions ---
    region_lookup = {}
    regions_out = []
    for r in regions:
        px, py = lnglat_to_pixel(r.get('lng', 0), r.get('lat', 0))
        entry = {
            'id': r.get('id'),
            'title': r.get('title', ''),
            'pixel_x': px,
            'pixel_y': py,
            'lng': r.get('lng'),
            'lat': r.get('lat'),
            'has_geojson': bool(r.get('geojson_data'))
        }
        regions_out.append(entry)
        region_lookup[r.get('id')] = entry
    print(f'[STEP2] regions processed: {len(regions_out)}', flush=True)

    # --- Process type_groups ---
    type_groups_out = []
    for tg in type_groups:
        type_ids = tg.get('type_ids', [])
        count = len(type_ids) if isinstance(type_ids, list) else 0
        type_groups_out.append({
            'id': tg.get('id'),
            'title': tg.get('title', ''),
            'type_count': count
        })
    print(f'[STEP2] type_groups processed: {len(type_groups_out)}', flush=True)

    # --- Process types ---
    types_out = []
    for t in types:
        region_ids = t.get('region_ids', '')
        types_out.append({
            'id': t.get('id'),
            'title': t.get('title', ''),
            'group_ids': t.get('group_ids', ''),
            'region_ids': str(region_ids) if region_ids else '',
            'icon': t.get('icon', '')
        })
    print(f'[STEP2] types processed: {len(types_out)}', flush=True)

    # --- Build output ---
    output = {
        'coordinate_bounds': {
            'lng': [LNG_MIN, LNG_MAX],
            'lat': [LAT_MIN, LAT_MAX]
        },
        'map_size': [4096, 4096],
        'areas': areas_out,
        'regions': regions_out,
        'type_groups': type_groups_out,
        'types': types_out,
        'total_areas': len(areas_out),
        'total_regions': len(regions_out),
        'total_types': len(types_out)
    }

    out_path = os.path.join(WORKDIR, 'aligned_points.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    fsize = os.path.getsize(out_path)
    print(f'[STEP3] aligned_points.json written ({fsize} bytes). areas={len(areas_out)} regions={len(regions_out)} types={len(types_out)} groups={len(type_groups_out)}', flush=True)

    # --- Update status.json ---
    status_path = os.path.join(WORKDIR, 'status.json')
    with open(status_path, 'r', encoding='utf-8') as f:
        status = json.load(f)

    status['web_data'] = {
        'status': 'done',
        'areas_count': len(areas_out),
        'regions_count': len(regions_out),
        'types_count': len(types_out),
        'file': 'aligned_points.json'
    }

    with open(status_path, 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    print(f'[STEP4] status.json updated. Final keys: {list(status.keys())}', flush=True)
    print('[DONE] All steps completed successfully.', flush=True)

except Exception as e:
    print(f'[ERROR] {type(e).__name__}: {e}', flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)