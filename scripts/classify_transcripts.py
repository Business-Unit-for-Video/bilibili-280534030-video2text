from __future__ import annotations
import argparse, csv, json, re
from collections import Counter
from pathlib import Path

CATEGORIES = {
    "人工智能与大模型": ("人工智能", "AI", "大模型", "语言模型", "多模态", "GPT", "Transformer", "深度学习", "机器学习", "神经网络", "推理模型", "生成式", "LLM"),
    "Agent、RAG与知识库": ("Agent", "智能体", "MCP", "A2A", "RAG", "知识库", "向量数据库", "向量库", "检索增强", "工作流", "LangChain", "提示词", "Prompt"),
    "编程与软件工程": ("编程", "代码", "程序员", "软件工程", "开发者", "API", "SDK", "GitHub", "Python", "JavaScript", "TypeScript", "数据库", "前端", "后端", "开源"),
    "云计算与基础设施": ("云计算", "云服务", "服务器", "容器", "Docker", "Kubernetes", "K8s", "部署", "运维", "GPU", "算力", "谷歌云", "AWS", "Azure", "网络", "芯片"),
    "产品、创业与商业": ("产品", "创业", "商业", "公司", "企业", "市场", "用户", "融资", "投资", "收入", "成本", "管理", "竞争", "营销", "商业模式"),
    "数据、安全与隐私": ("数据安全", "网络安全", "安全", "隐私", "权限", "漏洞", "攻击", "加密", "数据治理", "个人信息", "合规", "风控"),
    "效率、学习与职场": ("效率", "学习", "职场", "工作", "时间管理", "方法论", "经验", "面试", "职业", "思维", "读书", "教育", "成长"),
    "互联网与科技观察": ("互联网", "科技", "数字化", "平台", "应用", "手机", "浏览器", "搜索", "谷歌", "微软", "苹果", "腾讯", "字节", "行业", "趋势"),
}

def read_transcript(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^标题：(.+)$", text, re.MULTILINE)
    title = match.group(1).strip() if match else path.stem
    body = text[text.find("\n\n") + 2:] if "\n\n" in text else text
    return title, body

def classify_text(text):
    folded = text.casefold(); scores = Counter(); matches = {}
    for category, keywords in CATEGORIES.items():
        found = [keyword for keyword in keywords if keyword.casefold() in folded]
        if found: matches[category] = found; scores[category] = len(found)
    if not scores: return {"primary_category": "待人工归类", "categories": [], "confidence": 0.0, "matched_keywords": {}}
    ordered = scores.most_common(); related = [category for category, score in ordered if score >= max(1, ordered[0][1] // 2)]
    return {"primary_category": ordered[0][0], "categories": related, "confidence": round(ordered[0][1] / sum(scores.values()), 3), "matched_keywords": {category: matches[category] for category in related}}

def classify(transcripts_dir):
    rows = []
    for path in sorted(transcripts_dir.glob("BV*.txt")):
        title, body = read_transcript(path)
        rows.append({"bvid": path.stem, "title": title, "transcript_file": str(path).replace("\\", "/"), "characters": len(body), **classify_text(body)})
    return rows, dict(Counter(row["primary_category"] for row in rows))

def write_outputs(rows, summary, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    fields = ("bvid", "title", "transcript_file", "characters", "primary_category", "categories", "confidence", "matched_keywords")
    with (output_dir / "video-classification.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in rows: writer.writerow({**row, "categories": "、".join(row["categories"]), "matched_keywords": json.dumps(row["matched_keywords"], ensure_ascii=False)})
    (output_dir / "video-classification.json").write_text(json.dumps({"total": len(rows), "summary": summary, "videos": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 视频主题分类", "", f"共分析 **{len(rows)}** 份转录文本。", "", "## 分类统计", "", "| 主分类 | 数量 |", "|---|---:|"]
    lines.extend(f"| {category} | {count} |" for category, count in sorted(summary.items(), key=lambda item: (-item[1], item[0])))
    lines += ["", "## 说明", "", "- 分类依据是转录正文关键词，不依赖原 B 站合集或分集。", "- 每个视频保留一个主分类，同时保留相关分类和命中的关键词。", "- 待人工归类表示正文没有命中当前规则，后续可人工调整。", "- 这是第一版可复核分类，不会修改原始转录文本。", ""]
    (output_dir / "video-classification.md").write_text("\n".join(lines), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--transcripts", type=Path, default=Path("transcripts")); parser.add_argument("--output", type=Path, default=Path("classification")); args = parser.parse_args()
    rows, summary = classify(args.transcripts); write_outputs(rows, summary, args.output); print(json.dumps({"total": len(rows), "summary": summary}, ensure_ascii=False)); return 0

if __name__ == "__main__": raise SystemExit(main())
