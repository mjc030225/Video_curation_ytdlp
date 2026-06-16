# generate_queries.py
# 基于 topics.json，为每个 topic 生成搜索关键词，输出到 queries.json
# 功能：
#   - 调用 LLM 生成中英关键词
#   - 自动去重（全局）
#   - 简单敏感词过滤
#   - 按 category 分组统计并输出 stats

import json
import os
import time
from typing import List, Dict, Tuple
from collections import defaultdict

from openai import OpenAI

# ================== 配置部分 ==================
#OPENAI_API_KEY ="YOUR API KEY HERE" # 换成自己的，也可以删掉这里改用环境变量
# 建议用环境变量 OPENAI_API_KEY，也可以直接在这里写死：
#OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "") #export OPENAI_API_KEY="sk-08a9973958ab4def96836b2981f3d523"
OPENAI_API_KEY="sk-08a9973958ab4def96836b2981f3d523"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen2.5-72b-instruct"  # 这里可以换成别的兼容模型

TOPIC_FILE = "topics8c400t.json"
OUTPUT_QUERIES_FILE = "queries.json"
OUTPUT_STATS_FILE = "query_stats.json"

# 每个 topic 生成多少条关键词（总数：中 + 英）
NUM_QUERIES_PER_TOPIC = 20

# 调用间隔，简单限速，避免打爆 QPS
REQUEST_INTERVAL_SECONDS = 0.5

# 简单敏感词黑名单（只做粗过滤）
BANNED_SUBSTRINGS = [
    # NSFW / 色情相关关键词（中英文）
    "porn", "pornography", "nude", "naked", "xxx", "sex", "sexy",
    "成人", "情色", "裸露", "裸体", "性爱", "性行为", "激情",
    # 暴力/血腥（保守一点）
    "gore", "beheading", "execution", "血腥", "斩首", "处决"
]

# ================== 初始化 LLM 客户端 ==================

client = OpenAI(api_key=OPENAI_API_KEY, base_url=BASE_URL)


# ================== 工具函数 ==================

def normalize_query(q: str) -> str:
    """
    用于去重的归一化操作：
    - 去除首尾空格
    - 把多空格压成一个空格
    - 转小写
    """
    q = q.strip()
    # 把各种空白变成单个空格
    parts = q.split()
    q_norm = " ".join(parts).lower()
    return q_norm


def is_query_banned(q: str) -> Tuple[bool, str]:
    """
    简单敏感词过滤：
    - 如果命中 BANNED_SUBSTRINGS，则返回 (True, reason)
    """
    q_lower = q.lower()
    for bad in BANNED_SUBSTRINGS:
        if bad in q_lower:
            return True, f"contains banned word: {bad}"
    return False, ""


def is_query_too_short_or_long(q: str, language: str) -> bool:
    """
    简单长度过滤：
    - 英文：太短（< 3 单词） / 太长（> 20 单词）丢弃
    - 中文：太短（< 4 字） / 太长（> 40 字）丢弃（非常粗略）
    """
    q_stripped = q.strip()
    if language == "en":
        words = q_stripped.split()
        if len(words) < 3 or len(words) > 20:
            return True
    elif language == "zh":
        length = len(q_stripped)
        if length < 4 or length > 40:
            return True
    else:
        # 未知语言，保守一点：只要不是特别离谱就保留
        if len(q_stripped) < 3:
            return True
    return False


# ================== Prompt 构造与 LLM 调用 ==================

def build_prompt_for_topic(topic: Dict) -> str:
    """
    根据单个 topic 构造 prompt。
    输出要求是 JSON 对象，包含一个 "queries": [...] 数组，
    这样方便用 response_format={"type": "json_object"} 解析。
    """
    category_zh = topic.get("category_name_zh", "")
    topic_zh = topic.get("topic_name_zh", "")
    topic_en = topic.get("topic_name_en", "")
    desc_zh = topic.get("description_zh", "")
    desc_en = topic.get("description_en", "")

    n = NUM_QUERIES_PER_TOPIC


    """
    Prompt中文注释：
    你是视频检索关键词专家，现在要为 4K 高清人体/人脸视频构建搜索词列表。
    已知一个主题（topic）：
        - 大类（中文）：{category_zh}
        - 主题名（中）：{topic_zh}
        - 主题名（英）：{topic_en}
        - 说明（中文）：{desc_zh}
        - 说明（英文）：{desc_en}

    请为这个主题生成一组适用于 YouTube 的搜索关键词。   
    要求：
    1. 至少生成 {n} 条，其中：
        - 约一半为英文（language="en"），一半为中文（language="zh"）；
        - 不要包含 “4k” 或 “ultra hd”等词；
        - 明确体现有人物/人像出现，而不是纯风景。
    2. 每条关键词长度 3–12 个词（英文）或 6–20 个汉字（中文）。
    3. 避免带有暴力、色情、仇恨、极端政治等敏感内容。）
    4. 以 JSON 对象输出，格式如下：）
        {{
            "queries": [
                {{
                    "language": "zh" or "en",
                    "query": "search keyword string",
                    "source_topic_en": "{topic_en}"
                }},
                ...
            ]
        }}

        注意：
            - 顶层必须是一个带 "queries" 字段的 JSON 对象；
            - 不要输出任何额外的解释文字。
    """

    prompt = f"""
You are a video search keyword expert. Build search keyword lists for a 4K human face/body video dataset.

Given a topic:
- Category (Chinese): {category_zh}
- Topic name (Chinese): {topic_zh}
- Topic name (English): {topic_en}
- Description (Chinese): {desc_zh}
- Description (English): {desc_en}

Generate a set of search keywords suitable for YouTube for this topic.

Requirements:
1. Generate at least {n} queries, where:
   - About half are English (language="en") and half are Chinese (language="zh").
   - Not including terms like "4k" or "ultra hd".
   - Clearly indicate people/human subjects rather than pure landscapes.
2. Each query should be 3–12 words (English) or 6–20 Chinese characters (Chinese).
3. Avoid violent, sexual, hateful, or extreme political content.
4. Output as a JSON object with the following format:
{{
  "queries": [
    {{
      "language": "zh" or "en",
      "query": "search keyword string",
      "source_topic_en": "{topic_en}"
    }},
    ...
  ]
}}

Notes:
- The top-level must be a JSON object with a "queries" field.
- Do not output any extra explanatory text.
"""
    return prompt.strip()


def call_llm_for_topic(topic: Dict) -> List[Dict]:
    """
    调用 LLM，为一个 topic 生成关键词列表。
    返回：[{language, query, source_topic_en, ...}, ...]
    """
    prompt = build_prompt_for_topic(topic)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=6000,
        temperature=0.7,
    )

    content = response.choices[0].message.content or ""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = cleaned[start : end + 1]
            try:
                data = json.loads(snippet)
            except json.JSONDecodeError:
                print("Warning: JSON decode failed, content snippet:")
                print(cleaned[:200])
                return []
        else:
            print("Warning: JSON decode failed, content snippet:")
            print(cleaned[:200])
            return []

    if not isinstance(data, dict) or "queries" not in data:
        print("Warning: unexpected JSON structure, expected {{\"queries\": [...]}}. Got:")
        print(str(data)[:200])
        return []

    queries = data["queries"]
    if not isinstance(queries, list):
        print("Warning: 'queries' is not a list, ignoring.")
        return []

    # 附加topic信息
    for q in queries:
        q["category_id"] = topic.get("category_id")
        q["category_name_zh"] = topic.get("category_name_zh")
        q["category_name_en"] = topic.get("category_name_en")
        q["topic_id"] = topic.get("topic_id")
        q["topic_name_en"] = topic.get("topic_name_en")
        q["topic_name_zh"] = topic.get("topic_name_zh")

    return queries


# ================== 主逻辑 ==================

def load_topics(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        topics = json.load(f)
    assert isinstance(topics, list), "topics.json 顶层应该是一个数组"
    return topics


def main():
    topics = load_topics(TOPIC_FILE)
    print(f"Loaded {len(topics)} topics from {TOPIC_FILE}")

    all_queries: List[Dict] = []
    seen_queries = set()  # 用 normalized query 去重

    # stats 用于按 category 分组统计
    stats = defaultdict(lambda: {
        "category_name_zh": "",
        "category_name_en": "",
        "num_topics": 0,
        "num_queries": 0
    })
    topic_seen_in_category = set()  # (category_id, topic_id)

    for idx, topic in enumerate(topics):
        category_id = topic.get("category_id")
        topic_id = topic.get("topic_id")
        topic_name_en = topic.get("topic_name_en")
        topic_name_zh = topic.get("topic_name_zh")

        print(f"[{idx+1}/{len(topics)}] Generating queries for topic "
              f"cat={category_id}, topic={topic_id} - {topic_name_en} / {topic_name_zh}")

        # 为统计记录 topic
        key_ct = (category_id, topic_id)
        if key_ct not in topic_seen_in_category:
            topic_seen_in_category.add(key_ct)
            cat_stat = stats[category_id]
            cat_stat["category_name_zh"] = topic.get("category_name_zh", "")
            cat_stat["category_name_en"] = topic.get("category_name_en", "")
            cat_stat["num_topics"] += 1

        try:
            queries_raw = call_llm_for_topic(topic)
        except Exception as e:
            print(f"Error when calling LLM for topic {topic_id}: {e}")
            queries_raw = []

        print(f"  -> LLM returned {len(queries_raw)} raw queries")

        # 过滤 & 去重
        kept = 0
        for q in queries_raw:
            query_text = q.get("query", "")
            language = q.get("language", "").lower()

            # 长度过滤
            if is_query_too_short_or_long(query_text, language):
                continue

            # 敏感词过滤
            banned, reason = is_query_banned(query_text)
            if banned:
                # print 出来看是什么被过滤了
                # print(f"Filtered query '{query_text}' because {reason}")
                continue

            # 全局去重
            norm = normalize_query(query_text)
            if norm in seen_queries:
                continue
            seen_queries.add(norm)

            all_queries.append(q)
            kept += 1

        print(f"  -> kept {kept} queries after filtering/dedup")

        # 更新统计：按 category 累加 query 数
        stats[category_id]["num_queries"] += kept

        time.sleep(REQUEST_INTERVAL_SECONDS)

    # 保存结果 queries.json
    with open(OUTPUT_QUERIES_FILE, "w", encoding="utf-8") as f:
        json.dump(all_queries, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Saved {len(all_queries)} queries to {OUTPUT_QUERIES_FILE}")

    # 生成并保存按 category 的统计信息
    stats_out = []
    for cat_id, info in sorted(stats.items(), key=lambda x: x[0]):
        stats_out.append({
            "category_id": cat_id,
            "category_name_zh": info["category_name_zh"],
            "category_name_en": info["category_name_en"],
            "num_topics": info["num_topics"],
            "num_queries": info["num_queries"]
        })

    with open(OUTPUT_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats_out, f, ensure_ascii=False, indent=2)

    print(f"Saved category stats to {OUTPUT_STATS_FILE}")
    print("\nCategory summary:")
    for s in stats_out:
        print(f"  [cat {s['category_id']}] {s['category_name_zh']} / "
              f"{s['category_name_en']} -> topics={s['num_topics']}, "
              f"queries={s['num_queries']}")


if __name__ == "__main__":
    main()
