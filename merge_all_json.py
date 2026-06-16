import json
import glob

all_data = []
files = sorted(glob.glob("search_result_nofps_part_*.json"))

print("Merging files:")
for f in files:
    print(" ", f)
    with open(f, "r", encoding="utf-8") as jf:
        part = json.load(jf)
        all_data.extend(part)

print("Total merged:", len(all_data))

with open("search_result_4k.json", "w", encoding="utf-8") as out:
    json.dump(all_data, out, ensure_ascii=False, indent=2)
