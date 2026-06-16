# How to Setup
~~~bash
# run parser 和 filter
python 4k_video_parser_lazy.py # coarse parser，可能不符合条件，这是使用原来的filter去过滤，lazy方法 速度快很多

sbatch filter_videos.slurm # 根据videoid去重， filter过滤4k30帧以上的视频

python merge_all_json.py # 合并json文件

python scene_spliter.py # 分割场景，并下载

~~~
