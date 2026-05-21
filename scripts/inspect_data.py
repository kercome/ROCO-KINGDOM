import json

path = r'D:\Roco_Navigation_Tool_Workspace\web_data.txt'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)
d = data['data']

# Show 2 complete type entries
print("=== SAMPLE TYPE ENTRIES (full keys) ===")
types = d.get('types', [])
for t in types[:2]:
    print(json.dumps(t, indent=2, ensure_ascii=False))
    print("---")

# Show 2 complete type_group entries
print("\n=== SAMPLE TYPE_GROUP ENTRIES ===")
for tg in d.get('type_groups', [])[:2]:
    print(json.dumps(tg, indent=2, ensure_ascii=False))
    print("---")

# Collect all lng/lat from areas and regions
all_coords = []
for a in d.get('areas', []):
    if a.get('lng') is not None and a.get('lat') is not None:
        all_coords.append((a['lng'], a['lat']))
for r in d.get('regions', []):
    if r.get('lng') is not None and r.get('lat') is not None:
        all_coords.append((r['lng'], r['lat']))

if all_coords:
    lngs = [c[0] for c in all_coords]
    lats = [c[1] for c in all_coords]
    print(f"\n=== COORDINATE EXTENT ===")
    print(f"lng: min={min(lngs):.6f}, max={max(lngs):.6f}")
    print(f"lat: min={min(lats):.6f}, max={max(lats):.6f}")
    print(f"Total coordinates: {len(all_coords)}")
    print(f"Sample raw coords: {all_coords[:5]}")

# Check action data
print("\n=== ACTION DATA ===")
action = d.get('action', {})
if isinstance(action, dict):
    print(f"Keys: {list(action.keys())}")
    # Show first key value briefly
    for k in list(action.keys())[:3]:
        v = action[k]
        v_str = str(v)[:200]
        print(f"  {k}: {v_str}")