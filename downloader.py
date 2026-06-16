import yt_dlp
import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# ========= 全局错误日志锁 =========
error_lock = threading.Lock()


def log_error(error_file, msg):
    """线程安全写入 error.txt"""
    with error_lock:
        with open(error_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")


def download_single_video_from_txt(idx, url, output_path, error_file, on_finish=None):
    try:
        url = url.split()[0]
        video_id = f"video_{idx:06d}"

        ydl_opts = {
            'format': 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(output_path, f"{video_id}.%(ext)s"),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except Exception as e:
        log_error(error_file, f"[TXT] {url} | {e}")

    finally:
        if on_finish:
            on_finish(1)


def download_single_video_from_json(idx, info, output_path, error_file, on_finish=None):
    video_id = info.get("video_id", f"video_{idx:06d}")
    url = info.get("url", "")

    try:
        ydl_opts = {
            'format': 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(output_path, f"{video_id}.%(ext)s"),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except Exception as e:
        log_error(error_file, f"[JSON] {video_id} | {url} | {e}")

    finally:
        if on_finish:
            on_finish(1)


def download_youtube_videos_from_file(
    file_path: str,
    output_path: str = "./output",
    max_workers: int = 4,
    error_file: str = "error.txt",
):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    os.makedirs(output_path, exist_ok=True)

    # 清空旧的 error.txt（避免混淆）
    open(error_file, "w", encoding="utf-8").close()

    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.endswith(".txt"):
            urls = [line.strip() for line in f if line.strip()]
            total = len(urls)

            with tqdm(total=total, desc="Downloading videos") as pbar:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [
                        executor.submit(
                            download_single_video_from_txt,
                            idx,
                            url,
                            output_path,
                            error_file,
                            on_finish=pbar.update,
                        )
                        for idx, url in enumerate(urls)
                    ]

                    for future in as_completed(futures):
                        future.result()

        else:
            infos = json.load(f)
            total = len(infos)

            with tqdm(total=total, desc="Downloading videos") as pbar:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [
                        executor.submit(
                            download_single_video_from_json,
                            idx,
                            info,
                            output_path,
                            error_file,
                            on_finish=pbar.update,
                        )
                        for idx, info in enumerate(infos)
                    ]

                    for future in as_completed(futures):
                        future.result()

    print("All done!")
    print(f"If any error occurred, check: {error_file}")


if __name__ == "__main__":
    # TXT 示例
    # download_youtube_videos_from_file("videos.txt", "./output", max_workers=4)

    # JSON 示例
    download_youtube_videos_from_file(
        "search_result_4k.json",
        "/home/700050058/4KHuman_Dateset/4K",
        max_workers=16,
        error_file="error.txt",
    )
