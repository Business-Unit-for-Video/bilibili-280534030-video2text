import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path("scripts").resolve()))
from classify_transcripts import classify_text, write_outputs

def test_classify_text_supports_multiple_related_topics():
    result = classify_text("我们用 Agent、MCP 和 RAG 搭建知识库，再通过 Python API 部署到云服务器。")
    assert "Agent、RAG与知识库" in result["categories"]

def test_classify_text_marks_unknown_as_manual():
    assert classify_text("这是一段没有技术关键词的内容。")["primary_category"] == "待人工归类"

def test_write_outputs_creates_reviewable_files(tmp_path: Path):
    row = {"bvid": "BVTEST", "title": "测试", "transcript_file": "transcripts/BVTEST.txt", "characters": 10, "primary_category": "测试", "categories": ["测试"], "confidence": 1.0, "matched_keywords": {"测试": ["测试"]}}
    write_outputs([row], {"测试": 1}, tmp_path)
    assert (tmp_path / "video-classification.csv").is_file()
    assert json.loads((tmp_path / "video-classification.json").read_text(encoding="utf-8"))["total"] == 1
