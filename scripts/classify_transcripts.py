from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


# 主题分类。关键词分为高信号词和低信号词；低信号词只用于补充，
# 避免“公司、产品、用户”等泛词压过视频真正讨论的技术主题。
CATEGORIES = {
    "人工智能与大模型": {
        "high": ("人工智能", "大模型", "语言模型", "多模态", "GPT", "Transformer", "深度学习", "机器学习", "神经网络", "推理模型", "生成式", "LLM", "DeepSeek", "预训练", "后训练", "注意力机制"),
        "low": ("AI", "模型", "智能"),
    },
    "Agent、RAG与知识库": {
        "high": ("Agent", "智能体", "MCP", "A2A", "RAG", "知识库", "向量数据库", "向量库", "检索增强", "LangChain", "OpenClaw", "Claude Code"),
        "low": ("工作流", "提示词", "Prompt", "代理"),
    },
    "编程与软件工程": {
        "high": ("编程", "代码", "程序员", "软件工程", "开发者", "API", "SDK", "GitHub", "Python", "JavaScript", "TypeScript", "数据库", "前端", "后端", "开源", "CLI", "编程助手"),
        "low": ("开发", "工程", "仓库", "代码库"),
    },
    "云计算与基础设施": {
        "high": ("云计算", "云服务", "服务器", "容器", "Docker", "Kubernetes", "K8s", "部署", "运维", "GPU", "算力", "谷歌云", "AWS", "Azure", "芯片", "数据中心", "思考工厂"),
        "low": ("网络", "基础设施", "计算"),
    },
    "产品、创业与商业": {
        "high": ("创业", "商业模式", "融资", "投资", "收入", "成本", "管理", "竞争", "营销", "董事会", "CEO", "供应链", "市场战略"),
        "low": ("产品", "公司", "企业", "市场", "用户", "商业"),
    },
    "数据、安全与隐私": {
        "high": ("数据安全", "网络安全", "隐私", "漏洞", "攻击", "加密", "数据治理", "个人信息", "合规", "风控", "换脸骗局", "安全事件"),
        "low": ("安全", "权限", "数据"),
    },
    "效率、学习与职场": {
        "high": ("效率", "学习", "职场", "时间管理", "方法论", "面试", "职业", "读书", "教育", "成长", "课程", "教程"),
        "low": ("工作", "经验", "思维", "技巧"),
    },
    "互联网与科技观察": {
        "high": ("互联网", "科技观察", "数字化", "平台", "手机", "浏览器", "搜索", "行业趋势", "发布会", "演讲", "机器人行业", "物理AI", "Neuralink"),
        "low": ("应用", "谷歌", "微软", "苹果", "腾讯", "字节", "行业", "趋势"),
    },
}


REMARK_TYPE_RULES = (
    ("无意义", "无意义"),
    ("实例课程", "课程/实操"),
    ("技术选型", "技术选型"),
    ("预训练技术", "技术"),
    ("新技术", "技术"),
    ("访谈、演讲", "访谈/演讲"),
    ("访谈", "访谈"),
    ("演讲", "访谈/演讲"),
    ("技术", "技术"),
    ("理论", "理论"),
    ("思想", "思想"),
    ("讨论", "讨论"),
    ("机器人行业", "行业观察"),
    ("物理AI", "技术"),
    ("知识点", "知识点"),
    ("技巧", "技巧"),
)


def read_transcript(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^标题：(.+)$", text, re.MULTILINE)
    title = match.group(1).strip() if match else ""
    cache_path = path.parent.parent / "state" / "video-titles.json"
    if cache_path.exists():
        title = json.loads(cache_path.read_text(encoding="utf-8")).get(path.stem, title)
    if title == path.stem:
        title = ""
    body = text[text.find("\n\n") + 2:] if "\n\n" in text else text
    return title, body


def load_remarks(csv_path: Path) -> dict[str, str]:
    """读取已有 CSV 的人工 remark；重新生成时绝不覆盖这些标注。"""
    if not csv_path.exists():
        return {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row.get("bvid", ""): row.get("remark", "") for row in csv.DictReader(handle) if row.get("bvid")}


def classify_text(title: str, body: str | None = None):
    # 兼容旧测试和外部调用：classify_text(text) 仍表示只按正文分类。
    if body is None:
        body = title
        title = ""
    title_folded = title.casefold()
    body_folded = body.casefold()
    scores = Counter()
    matches = {}
    for category, groups in CATEGORIES.items():
        found = []
        score = 0.0
        for keyword in groups["high"]:
            folded = keyword.casefold()
            title_hits = title_folded.count(folded)
            body_hits = min(body_folded.count(folded), 3)
            if title_hits or body_hits:
                found.append(keyword)
                score += title_hits * 6.0 + body_hits * 1.5
        for keyword in groups["low"]:
            folded = keyword.casefold()
            title_hits = title_folded.count(folded)
            body_hits = min(body_folded.count(folded), 2)
            if title_hits or body_hits:
                found.append(keyword)
                score += title_hits * 2.0 + body_hits * 0.35
        if score:
            scores[category] = score
            matches[category] = found
    if not scores:
        return {"primary_category": "待人工归类", "categories": [], "confidence": 0.0, "matched_keywords": {}}
    ordered = scores.most_common()
    best = ordered[0][1]
    # 只保留接近主分类的相关主题，避免每个视频被所有泛词标签污染。
    related = [category for category, score in ordered if score >= max(2.0, best * 0.42)]
    total = sum(scores.values())
    return {
        "primary_category": ordered[0][0],
        "categories": related,
        "confidence": round(best / total, 3),
        "matched_keywords": {category: matches[category] for category in related},
    }


def infer_content_type(remark: str, title: str, body: str) -> str:
    """优先采用用户 remark；未标注的视频只做保守推断，便于后续人工复核。"""
    clean = (remark or "").strip()
    if clean:
        for marker, content_type in REMARK_TYPE_RULES:
            if marker in clean:
                return content_type
        return clean
    # 未标注内容只看标题，避免转录正文中提到“课程/工作/行业”等词而被误判。
    text = title
    if re.search(r"访谈|对话|演讲|发布会", text, re.IGNORECASE):
        return "访谈/演讲"
    if re.search(r"教程|实操|入门|怎么|如何|介绍|指南", text, re.IGNORECASE):
        return "课程/实操"
    if re.search(r"理论|原理|机制|为什么", text, re.IGNORECASE):
        return "理论"
    if re.search(r"行业|市场|公司|董事会|供应链|趋势", text, re.IGNORECASE):
        return "行业观察"
    return "待人工确认"


def classify(transcripts_dir: Path, remarks_path: Path):
    remarks = load_remarks(remarks_path)
    rows = []
    for path in sorted(transcripts_dir.glob("BV*.txt")):
        title, body = read_transcript(path)
        remark = remarks.get(path.stem, "")
        topic = classify_text(title, body)
        rows.append(
            {
                "bvid": path.stem,
                "title": title,
                "transcript_file": str(path).replace("\\", "/"),
                "characters": len(body),
                **topic,
                "content_type": infer_content_type(remark, title, body),
                "remark": remark,
            }
        )
    topic_summary = dict(Counter(row["primary_category"] for row in rows))
    content_summary = dict(Counter(row["content_type"] for row in rows))
    return rows, topic_summary, content_summary


def write_outputs(rows, topic_summary, output_dir: Path, content_summary=None):
    # 保持旧调用约定 write_outputs(rows, summary, output_dir) 可用。
    if content_summary is None:
        content_summary = dict(Counter(row.get("content_type", "待人工确认") for row in rows))
    output_dir.mkdir(parents=True, exist_ok=True)
    fields = ("bvid", "title", "transcript_file", "characters", "primary_category", "categories", "confidence", "matched_keywords", "content_type", "remark")
    with (output_dir / "video-classification.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "categories": "、".join(row["categories"]), "matched_keywords": json.dumps(row["matched_keywords"], ensure_ascii=False)})
    payload = {"total": len(rows), "summary": topic_summary, "content_type_summary": content_summary, "videos": rows}
    (output_dir / "video-classification.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 视频主题与内容类型分类", "", f"共分析 **{len(rows)}** 份转录文本。", "", "## 内容类型统计（优先采用人工 remark）", "", "| 内容类型 | 数量 |", "|---|---:|"]
    lines.extend(f"| {category} | {count} |" for category, count in sorted(content_summary.items(), key=lambda item: (-item[1], item[0])))
    lines += ["", "## 主题分类统计", "", "| 主分类 | 数量 |", "|---|---:|"]
    lines.extend(f"| {category} | {count} |" for category, count in sorted(topic_summary.items(), key=lambda item: (-item[1], item[0])))
    lines += [
        "",
        "## 规则说明",
        "",
        "- `remark` 是人工标注，原文保留；`content_type` 优先按 remark 归一化。",
        "- `primary_category` 和 `categories` 是主题分类，使用标题强信号与正文关键词加权。",
        "- 标题命中权重高于正文，泛化词权重较低，以减少技术视频被误归为商业类。",
        "- 没有 remark 的内容类型仅作保守推断，标为“待人工确认”的视频可继续补充。",
        "- 不修改任何原始转录文本。",
        "",
    ]
    (output_dir / "video-classification.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcripts", type=Path, default=Path("transcripts"))
    parser.add_argument("--output", type=Path, default=Path("classification"))
    args = parser.parse_args()
    csv_path = args.output / "video-classification.csv"
    rows, topic_summary, content_summary = classify(args.transcripts, csv_path)
    write_outputs(rows, topic_summary, args.output, content_summary)
    print(json.dumps({"total": len(rows), "summary": topic_summary, "content_type_summary": content_summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
