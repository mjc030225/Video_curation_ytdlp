import yt_dlp
import os
import json
from copy import deepcopy
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_SEARCH = 20
# MAX_LIMIT = 300

BS_REQUIREMENT = {
    "height": 2160,
    "fps": 30,
    "duration": 10,
}

PROGRESS_DIR = "lazy_progress"
DONE_FILE = os.path.join(PROGRESS_DIR, "done_keywords.json")

os.makedirs(PROGRESS_DIR, exist_ok=True)


def load_done_keywords():
    if os.path.exists(DONE_FILE):
        with open(DONE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_done_keywords(done_set):
    with open(DONE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(done_set)), f, indent=2)


def extract_single_video_info(idx, line):
    keyword = line["query"]
    encoded_kw = quote_plus(keyword)

    save_path = os.path.join(PROGRESS_DIR, f"keyword_{idx}.json")

    if os.path.exists(save_path):
        with open(save_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"[START] {idx}: {keyword}")
    seen_ids = set()

    search_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
    }

    with yt_dlp.YoutubeDL(search_opts) as ydl:
        search_query = (
                "https://www.youtube.com/results?"
                f"search_query={encoded_kw}&sp=EgQwAXAB"
            )
        search_result = ydl.extract_info(search_query, download=False)

    entries = search_result.get("entries", [])
    qualified = []
    for entry in entries:
        if len(qualified) >= MAX_SEARCH:
            break
        vid = entry.get("id")
        if not vid or vid in seen_ids:
            continue
        seen_ids.add(vid)

        duration = entry.get("duration") or 0
        
        video_info = deepcopy(line)
        video_info.update({
            "platform": "Youtube",
            "title": entry.get("title"),
            "video_id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "duration": duration,
            "description": entry.get("description"),
        })
        # video_info.update(video_info)
        if duration >= BS_REQUIREMENT["duration"]:
            qualified.append(video_info)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(qualified, f, ensure_ascii=False, indent=2)
    return qualified
    

def extract_youtube_info_from_file(file_path, max_workers=16):
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        lines = json.load(f)

    if not isinstance(lines, list):
        raise ValueError("JSON 文件必须是 list")

    done_keywords = load_done_keywords()
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}

        for idx, line in enumerate(lines):
            if idx in done_keywords:
                continue
            future = executor.submit(extract_single_video_info, idx, line)
            future_map[future] = idx

        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                videos = future.result()
                results.extend(videos)
                done_keywords.add(idx)
                save_done_keywords(done_keywords)
            except Exception as e:
                print(f"[ERROR] keyword {idx}: {e}")

    return results


if __name__ == "__main__":
    videos_info = extract_youtube_info_from_file(
        "queries_v1.json",
        max_workers=min(16, os.cpu_count() * 2)
    )
    # videos_info = extract_youtube_info_from_file(
    #     "query_test.json",
    #     max_workers=min(16, os.cpu_count() * 2)
    # )
    output_path = "search_result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(videos_info, f, ensure_ascii=False, indent=2)

    print(f"\n已保存到 {output_path}")
    
