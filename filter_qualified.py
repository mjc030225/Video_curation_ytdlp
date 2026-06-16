import json
from yt_dlp import YoutubeDL
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from tqdm import tqdm

def deduplicate_by_video_id(data):
    seen = set()
    unique_data = []

    for item in data:
        vid = item.get("video_id")
        if not vid:
            continue
        if vid in seen:
            continue
        seen.add(vid)
        unique_data.append(item)

    print("原始条数:", len(data))
    print("去重后条数:", len(unique_data))
    return unique_data

def get_best_video_info(url):
    """
    返回最高 resolution + fps 的视频信息
    """
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "concurrent_fragment_downloads": 1,
        "no_warnings": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    description = info.get("description")
    best_format = None
    max_score = 0

    for f in info.get("formats", []):
        height = f.get("height") or 0
        fps = f.get("fps") or 0

        if f.get("vcodec") == "none":
            continue

        score = height * 100 + fps
        if score > max_score:
            max_score = score
            best_format = f

    if not best_format:
        return None

    return {
        "description": description,
        "resolution_height": best_format.get("height"),
        "resolution_width": best_format.get("width"),
        "fps": best_format.get("fps"),
    }


def process_item(item, counter, lock):
    url = item.get("url")
    if not url:
        return None

    try:
        video_info = get_best_video_info(url)
    except Exception as e:
        print(f"解析失败: {url} -> {e}")
        return None

    if not video_info:
        return None

    height = video_info["resolution_height"]
    fps = video_info["fps"]

    # if height and height >= 2160 and fps and fps >= 30:
    if height and height >= 2160:
        item["description"] = video_info["description"]
        item["resolution_height"] = height
        item["resolution_width"] = video_info["resolution_width"]
        item["fps"] = fps

        with lock:
            counter["success"] += 1

        return item

    return None


def filter_json(data, workers=8):
    # data = deduplicate_by_video_id(data)

    lock = Lock()
    counter = {"success": 0}
    filtered = []

    total = len(data)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(process_item, item, counter, lock)
            for item in data
        ]

        with tqdm(total=total, desc="Processing", ncols=100) as pbar:
            for future in as_completed(futures):
                result = future.result()
                if result:
                    filtered.append(result)

                pbar.update(1)
                pbar.set_postfix(
                    success=f"{counter['success']}/{total}"
                )

    print("符合条件条数(4K & fps>30):", len(filtered))
    return filtered

def slice_by_array_id(data, task_id, task_count):
    """
    把数据均匀切分给不同 array task
    """
    return data[task_id::task_count]

import os
import json

if __name__ == "__main__":
    with open("search_result.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Slurm array 信息
    task_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", 0))
    task_count = int(os.environ.get("SLURM_ARRAY_TASK_COUNT", 1))

    print(f"Array task {task_id}/{task_count}")
    filter_data = deduplicate_by_video_id(data)

    # 每个任务只处理自己的那一份
    filter_data = slice_by_array_id(filter_data, task_id, task_count)

    filter_data = filter_json(filter_data)

    out_file = f"search_result_nofps_part_{task_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(filter_data, f, ensure_ascii=False, indent=2)

    print(f"Saved {out_file}, count={len(filter_data)}")

