# Filter process
1. 先根据关键词过滤掉绝大多数不符合条件的视频，youtube可以用关键词去筛选需要的条件，例如，是否知识共享，是否4k，`4k_video_parser_lazy.py`
2. 得到的json文件还需要细筛选，因为不完全正确，用`4k_video_parser_strict.py`, 可以用filter_video.slurm
3. 然后可以用scene_spliter.py 去划分场景。

# How to Setup
~~~bash
# run parser 和 filter
python 4k_video_parser_lazy.py # coarse parser，可能不符合条件，这是使用原来的filter去过滤，lazy方法 速度快很多

sbatch filter_videos.slurm # 根据videoid去重， filter过滤4k30帧以上的视频

python merge_all_json.py # 合并json文件

python scene_spliter.py # 分割场景，并下载

~~~
