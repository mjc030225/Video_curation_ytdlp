### topics8c400t.json 为 LLM 生成的 8 类主题共 400 个 topic
> 示例：
> ```json
> {
>   "category_id": 1,
>   "category_name_zh": "场景/设置",
>   "category_name_en": "Scene / Setting",
>   "topic_id": 1,
>   "topic_name_zh": "城市街头",
>   "topic_name_en": "City Street",
>   "description_zh": "人们在繁忙的城市街道上行走，车辆穿梭其间。",
>   "description_en": "People walking on busy city streets with vehicles passing by."
> }
> ```

### queries.json 为 LLM 生成的 query，每个 topic 生成约 20 条关键词（中 + 英）
> 示例：
> ```json
> {
>    "language": "en",
>    "query": "4k people walking city street",
>    "source_topic_en": "City Street",
>    "category_id": 1,
>    "category_name_zh": "场景/设置",
>    "category_name_en": "Scene / Setting",
>    "topic_id": 1,
>    "topic_name_en": "City Street",
>    "topic_name_zh": "城市街头"
>  }
> ```


### query_stats.json 为生成 query 结果的统计
> 如第一类：
> ```json
> {
>     "category_id": 1,
>     "category_name_zh": "场景/设置",
>     "category_name_en": "Scene / Setting",
>     "num_topics": 50,
>     "num_queries": 996
>   }
> ```

### 希望爬虫时候生成的视频元数据信息：
> 爬取的元数据示例：
> ```json
> {
> "video_id": "abc123",
> "platform": "youtube",
> "query": "4k news anchor close up in studio",
> "category_id": 2,
> "category_name_zh": "角色/身份",
> "category_name_en": "Character Roles / Identities",
> "topic_id": 15,
> "topic_name_zh": "记者",
> "topic_name_en": "Journalist",
> ####一些视频相关的information，尽可能详细吧
> "title": "...",
> "duration_sec": 120,
> "resolution_height": 2160,
> "resolution_width": 2160,
> "channel_id": "...",
> "url": "https://...",
> ... 
> }
> ```

# How to Setup
~~~bash
# run parser 和 filter
python 4k_video_parser_lazy.py # coarse parser，可能不符合条件

sbatch filter_videos.slurm # 根据videoid去重， filter过滤4k30帧以上的视频

python merge_all_json.py # 合并json文件

python scene_spliter.py # 分割场景，并下载

~~~

爬取结果：
10s以上， 4k30以上共22530
10s以上，4k的共30942