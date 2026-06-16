# generate_topics.py
# 用 LLM 自动生成 4K 人体/人脸视频的 topic 体系，输出到 topics.json

import json
import os
from typing import List, Dict

from openai import OpenAI

# ======= 配置部分 =======
#OPENAI_API_KEY ="YOUR API KEY HERE" # 换成自己的，也可以删掉这里改用环境变量
#OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "") #export OPENAI_API_KEY="sk-08a9973958ab4def96836b2981f3d523"
OPENAI_API_KEY="sk-08a9973958ab4def96836b2981f3d523"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen2.5-72b-instruct"
OUTPUT_FILE = "topics8c400t.json"

# 希望生成的类别数与总 topic 数（只是建议值，交给 LLM 实现）
NUM_CATEGORIES = 8
APPROX_TOPICS_TOTAL = 400


# ======= LLM 调用封装 =======

client = OpenAI(api_key=OPENAI_API_KEY, base_url=BASE_URL)

"""
你要面向的是 “4K 人体/人脸视频数据集”，典型任务包括：
- 视频人脸高清化 / 修复
- 个性化人物视频生成
- 视频换脸 / 换头
- 数字人 / 数字分身 / 说话人生成
- 人体姿态与动作建模（走路、跑步、跳舞、健身等）
- 多人对话、会议、课堂等社交互动场景

以下是一些示例维度（仅供参考，你可以扩展）：
- 场景 / 场合：街景、办公室、会议室、教室、客厅、厨房、健身房、直播间、演播室、公园、商场、公共交通等。
- 人物角色 / 身份：新闻主播、vlogger、教师、医生、客服、商务人士、游戏主播、健身教练、舞者、演员、儿童、老人等。
- 动作 / 行为：走路、跑步、讲话、演讲、比手势、打电话、视频会议、阅读、写字、做饭、健身训练、跳舞等。
- 镜头类型：人脸特写、半身、全身、群像、静态机位、手持跟拍、俯拍、仰拍、肩后视角等。
- 表情与情绪：中性、微笑、大笑、严肃、惊讶、愤怒、难过、困惑、兴奋、疲惫、专注聆听等。
- 光照与风格：室内自然光、夜晚暖光、办公室冷光、演播室三点布光、背光、阴天户外、黄金时段、霓虹夜景、屏幕光等。
- 多人社交：会议讨论、头脑风暴、家庭聚会、朋友聚餐、课堂互动、团体健身课、排队、观众席等。

数据集必须避免 NSFW / 暴力 / 极端政治 / 仇恨等敏感内容。
"""

SEED_DIMENSIONS = """
You are working on a “4K human face/body video dataset”. Typical tasks include:
- Face restoration / enhancement in videos
- Personalized character video generation
- Face swap / head swap in videos
- Digital human / avatar / talking-head generation
- Human pose and motion modeling (walking, running, dancing, fitness, etc.)
- Social interaction scenes such as conversations, meetings, and classrooms

Here are example dimensions (for reference, you can extend them):
- Scene / setting: street, office, meeting room, classroom, living room, kitchen, gym, livestream room, studio, park, mall, public transit, etc.
- Character roles / identities: news anchor, vlogger, teacher, doctor, customer service, business professional, game streamer, fitness coach, dancer, actor, child, senior, etc.
- Actions / behaviors: walking, running, speaking, presenting, gesturing, phone call, video meeting, reading, writing, cooking, workout training, dancing, etc.
- Shot types: facial close-up, upper-body, full-body, group shot, static camera, handheld follow, overhead, low-angle, over-the-shoulder, etc.
- Expressions & emotions: neutral, smile, laugh, serious, surprise, anger, sadness, confusion, excitement, fatigue, attentive listening, etc.
- Lighting & style: indoor natural light, warm night light, cool office light, three-point studio lighting, backlight, overcast outdoor, golden hour, neon night, screen light, etc.
- Social interactions: meeting discussion, brainstorming, family gathering, friends' dinner, classroom interaction, group fitness class, queueing, audience seating, etc.

The dataset must avoid NSFW / violence / extreme politics / hate and other sensitive content.
"""


def build_prompt_for_topics() -> str:
    """
    构造一个一次性生成所有 topic 的 prompt。
    prompt: 你是视频数据集构建专家，目标是为 “4K 人体/人脸视频数据集” 设计搜索用的主题体系。
    {SEED_DIMENSIONS}

    请你设计一个主题体系，满足以下要求：
    1. 一共设计 {NUM_CATEGORIES} 个大类（category），每个大类下包含若干 topic，总 topic 数量大约为 {APPROX_TOPICS_TOTAL}（±20 都可以）。
    2. 所有 topic 必须与 “有人物 / 人体 / 人脸出现” 有关，不能是纯风景或静物。）
    3. 尽量覆盖：
        - 不同场景（家庭、办公、教学、医疗、户外、街景、演播室、直播间等）；
        - 不同人物角色、年龄段；
        - 不同动作、表情、光照与拍摄方式；
        - 多人互动和单人讲话场景。
    4. 明确排除 NSFW、过度暴力、极端政治和仇恨内容。
    5. 输出为一个 JSON 数组（array），其中每个元素代表一个 topic，对应字段为：
        - "category_id": 整数，从 1 开始编号；
        - "category_name_zh": 该类别的中文名称（例如 “场景与环境”）；
        - "category_name_en": 对应的英文名称（例如 “Scene and Environment”）；
        - "topic_id": 在该类别内从 1 开始编号的整数；
        - "topic_name_zh": topic 的中文短语（例如 “办公室工位工作场景”）；
        - "topic_name_en": topic 的英文短语（例如 "office desk working scene"）；
        - "description_zh": 1–3 句中文，简要说明这个 topic 适合哪些视频内容（重点描述人物、动作、场景、镜头特征）。
        - "description_en": 1–3 句英文，语义与中文描述一致。

    6. JSON 顶层必须是一个数组，形如：
        [
            {{
                "category_id": 1,
                "category_name_zh": "...",
                "category_name_en": "...",
                "topic_id": 1,
                "topic_name_zh": "...",
                "topic_name_en": "...",
                "description_zh": "...",
                "description_en": "..."
            },
            ...
        ]

    只输出 JSON 数组，不要包含任何其他文字。
    """
    prompt = f"""
You are a video dataset construction expert. Your goal is to design a topic taxonomy for search in a “4K human face/body video dataset”.

{SEED_DIMENSIONS}

Please design a topic taxonomy that meets the following requirements:

1. Create {NUM_CATEGORIES} top-level categories. Each category contains several topics, and the total number of topics is approximately {APPROX_TOPICS_TOTAL} (±20 is OK).
2. Every topic must involve people / human bodies / faces; no pure landscape or still-life content.
3. Try to cover:
   - Different scenes (home, office, education, medical, outdoor, street, studio, livestream room, etc.).
   - Different character roles and age groups.
   - Different actions, expressions, lighting, and shooting styles.
   - Multi-person interaction and single-person speaking scenarios.
4. Explicitly exclude NSFW, excessive violence, extreme politics, and hateful content.
5. Output a JSON array, where each element represents a topic with the following fields:
   - "category_id": integer, starting from 1.
   - "category_name_zh": Chinese category name.
   - "category_name_en": English category name (e.g., “Scene and Environment”).
   - "topic_id": integer, starting from 1 within the category.
   - "topic_name_zh": Chinese short phrase for the topic.
   - "topic_name_en": English short phrase for the topic (e.g., "office desk working scene").
   - "description_zh": 1–3 sentences in Chinese describing suitable video content (focus on people, actions, scene, and shot characteristics).
   - "description_en": 1–3 sentences in English, semantically aligned with the Chinese description.

6. The JSON top-level must be an array, like this:[
  {{
    "category_id": 1,
    "category_name_zh": "...",
    "category_name_en": "...",
    "topic_id": 1,
    "topic_name_zh": "...",
    "topic_name_en": "...",
    "description_zh": "...",
    "description_en": "..."
  }},
  ...
]

Only output the JSON array, with no extra text.
"""
    return prompt.strip()

def build_prompt_for_categories() -> str:
    """
    构造生成 category 列表的 prompt。
    """
    prompt = f"""
You are a video dataset construction expert. Your goal is to design a topic taxonomy for search in a “4K human face/body video dataset”.

{SEED_DIMENSIONS}

Please output {NUM_CATEGORIES} top-level categories only. Each element must include:
  - "category_id": integer, starting from 1
  - "category_name_zh"
  - "category_name_en"

Output a JSON array only, no extra text.
"""
    return prompt.strip()


def build_prompt_for_category_topics(category: Dict, target_count: int) -> str:
    """
    构造某一类别下 topics 列表的 prompt。
    """
    prompt = f"""
You are a video dataset construction expert. Generate topics for the following category.

Category:
  - category_id: {category["category_id"]}
  - category_name_zh: {category["category_name_zh"]}
  - category_name_en: {category["category_name_en"]}

Generate about {target_count} topics under this category. Each topic must include:
  - "category_id": integer, same as above
  - "category_name_zh"
  - "category_name_en"
  - "topic_id": integer, starting from 1 within this category
  - "topic_name_zh"
  - "topic_name_en"
  - "description_zh": 1–3 Chinese sentences
  - "description_en": 1–3 English sentences aligned with Chinese

All topics must involve people / human bodies / faces; avoid NSFW, violence, extreme politics, hate.
Output a JSON array only, no extra text.
"""
    return prompt.strip()


def parse_json_array(content: str) -> List[Dict]:
    """
    解析 JSON 数组；若夹杂多余文本，尝试抽取最外层 JSON 数组。
    """
    cleaned = content.strip()
    if cleaned.startswith("```"):
        # Strip markdown code fences like ```json ... ```
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1 and end > start:
            snippet = cleaned[start : end + 1]
            data = json.loads(snippet)
        else:
            print("JSON 解析失败，LLM 输出前 500 字符为：")
            print(cleaned[:500])
            raise

    if isinstance(data, dict):
        if "topics" in data and isinstance(data["topics"], list):
            data = data["topics"]
        elif "data" in data and isinstance(data["data"], list):
            data = data["data"]
        else:
            raise ValueError("LLM 返回的 JSON 结构不是预期的数组形式。")

    if not isinstance(data, list):
        raise ValueError("最终解析结果不是数组。")

    return data


def call_llm_for_topics() -> List[Dict]:
    """
    分步调用 LLM 生成所有 topic（先类别，后逐类生成 topic）。
    返回：列表，每个元素是一个 topic dict。
    """
    # 先生成 categories
    cat_prompt = build_prompt_for_categories()
    cat_resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": cat_prompt}],
        max_tokens=6000,
        temperature=0.5,
    )
    categories = parse_json_array(cat_resp.choices[0].message.content or "")

    # 为每个类别分配 topic 数量，避免一次性输出过长被截断
    base = APPROX_TOPICS_TOTAL // NUM_CATEGORIES
    remainder = APPROX_TOPICS_TOTAL % NUM_CATEGORIES

    topics: List[Dict] = []
    for idx, cat in enumerate(categories):
        target_count = base + (1 if idx < remainder else 0)
        topic_prompt = build_prompt_for_category_topics(cat, target_count)
        topic_resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": topic_prompt}],
            max_tokens=6000,
            temperature=0.6,
        )
        cat_topics = parse_json_array(topic_resp.choices[0].message.content or "")
        topics.extend(cat_topics)

    # 可以在这里做一些轻微的检查或排序（可选）
    topics.sort(key=lambda x: (x.get("category_id", 0), x.get("topic_id", 0)))

    return topics


def main():
    topics = call_llm_for_topics()
    print(f"Generated {len(topics)} topics.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)

    print(f"Saved topics to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
