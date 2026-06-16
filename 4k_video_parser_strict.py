import yt_dlp
import os
import json
from copy import deepcopy
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_SEARCH = 10
MAX_LIMIT = 300

BS_REQUIREMENT = {
    "height": 2160,
    "fps": 30,
    "duration": 10,
}

PROGRESS_DIR = "strict_progress"
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


def get_best_video_resolution(info):
    best = None
    for f in info.get("formats", []):
        if f.get("vcodec") in (None, "none"):
            continue
        h = f.get("height") or 0
        fps = f.get("fps") or 0
        if h >= BS_REQUIREMENT["height"] and fps >= BS_REQUIREMENT["fps"]:
            if not best or (h, fps) > (best["height"], best["fps"]):
                best = f

    if not best:
        return None

    return {
        "resolution_height": best.get("height"),
        "resolution_width": best.get("width"),
        "fps": best.get("fps"),
    }


def fetch_full_video_info(video_id):
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        return ydl.extract_info(
            f"https://www.youtube.com/watch?v={video_id}",
            download=False
        )



def extract_single_video_info(idx, line):
    keyword = line["query"]
    save_path = os.path.join(PROGRESS_DIR, f"keyword_{idx}.json")

    if os.path.exists(save_path):
        with open(save_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"[START] {idx}: {keyword}")

    qualified_60 = []
    qualified_30 = []
    seen_ids = set()


    search_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
    }

    with yt_dlp.YoutubeDL(search_opts) as ydl:
        search_query = f"ytsearch{MAX_LIMIT}:{keyword}"
        search_result = ydl.extract_info(search_query, download=False)

    entries = search_result.get("entries", [])

    for entry in entries:
        if len(qualified_60) + len(qualified_30) >= MAX_SEARCH:
            break

        vid = entry.get("id")
        if not vid or vid in seen_ids:
            continue
        seen_ids.add(vid)

        duration = entry.get("duration") or 0
        if duration < BS_REQUIREMENT["duration"]:
            continue

        try:
            info = fetch_full_video_info(vid)
        except Exception:
            continue

        best = get_best_video_resolution(info)
        if not best:
            continue

        video_info = deepcopy(line)
        video_info.update({
            "platform": "Youtube",
            "title": info.get("title"),
            "video_id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "duration": duration,
            "description": info.get("description"),
        })
        video_info.update(best)

        if best["fps"] >= 60:
            qualified_60.append(video_info)
        else:
            qualified_30.append(video_info)

    final_videos = qualified_60 + qualified_30

    if len(final_videos) < MAX_SEARCH:
        raise RuntimeError(
            f"关键词 [{keyword}] 仅找到 {len(final_videos)} 条合格视频"
        )

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(final_videos[:MAX_SEARCH], f, ensure_ascii=False, indent=2)

    print(f"[DONE] {idx}: {keyword}")
    return final_videos[:MAX_SEARCH]



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
    
