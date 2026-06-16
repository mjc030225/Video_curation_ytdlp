import yt_dlp
import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# ========= 全局错误日志锁 =========
error_lock = threading.Lock()


def log_error(error_file, msg):
    with error_lock:
        with open(error_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")


def get_slurm_task_info():
    """获取 Slurm array 信息"""
    task_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", 0))
    task_count = int(os.environ.get("SLURM_ARRAY_TASK_COUNT", 1))
    return task_id, task_count


def split_data(data, task_id, task_count):
    """按 Slurm task 切分数据"""
    total = len(data)
    chunk_size = (total + task_count - 1) // task_count
    start = task_id * chunk_size
    end = min(start + chunk_size, total)
    return data[start:end], start


def download_youtube_videos_from_json(
    json_path,
    output_path,
    max_workers=4,
    error_file="error.txt",
):
    os.makedirs(output_path, exist_ok=True)

    task_id, task_count = get_slurm_task_info()

    with open(json_path, "r", encoding="utf-8") as f:
        infos = json.load(f)

    # 🔥 Slurm 切分
    sub_infos, global_start_idx = split_data(infos, task_id, task_count)

    print(
        f"[Task {task_id}/{task_count}] "
        f"Processing {len(sub_infos)} videos "
        f"(global index {global_start_idx} ~ {global_start_idx + len(sub_infos) - 1})"
    )

    with tqdm(total=len(sub_infos), desc=f"Task {task_id}") as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            for local_idx, info in enumerate(sub_infos):
                global_idx = global_start_idx + local_idx
                video_id = info.get("video_id", f"video_{global_idx:06d}")
                url = info.get("url", "").split()[0]

                futures.append(
                    executor.submit(
                        download_single_video,
                        global_idx,
                        video_id,
                        url,
                        output_path,
                        error_file,
                        pbar.update,
                    )
                )

            for f in as_completed(futures):
                f.result()

    print(f"[Task {task_id}] Done!")
import time

def download_single_video(
    idx,
    video_id,
    url,
    output_path,
    error_file,
    on_finish,
    max_retries=3,
    retry_sleep=5,
):
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            ydl_opts = {
                'format': 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]',
                'merge_output_format': 'mp4',
                'outtmpl': os.path.join(output_path, f"{video_id}.%(ext)s"),
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'cookiefile': '/home/700050058/cookies.txt',
                # 🔥 yt-dlp 自带重试（双保险）
                'retries': 5,
                'fragment_retries': 5,
                'socket_timeout': 30,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # ✅ 成功直接返回
            return

        except Exception as e:
            last_error = str(e)
            print(
                f"[Retry {attempt}/{max_retries}] "
                f"{video_id} failed: {e}"
            )

            if attempt < max_retries:
                time.sleep(retry_sleep)

    # ❌ 全部失败才记录
    log_error(
        error_file,
        f"{video_id} | {url} | FAILED after {max_retries} retries | {last_error}"
    )

    on_finish(1)


if __name__ == "__main__":
    download_youtube_videos_from_json(
        "search_result_4k.json",
        "/home/700050058/4KHuman_Dateset/4K",
        max_workers=2,  # 👈 每个 Slurm 任务内部线程数
        error_file="error.txt",
    )
