from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path("scripts").resolve()))
import transcribe_bili


def test_repo_layout_is_ready_for_first_run():
    assert Path("scripts/transcribe_bili.py").is_file()
    assert Path("scripts/transcription_integrity.py").is_file()
    assert Path(".github/workflows/transcribe.yml").is_file()
    assert Path(".github/workflows/retry_failed_transcripts.yml").is_file()
    assert Path("state/.gitkeep").is_file()
    assert Path("transcripts/.gitkeep").is_file()


def test_workflows_target_space_and_repository_secret():
    workflow = Path(".github/workflows/transcribe.yml").read_text(encoding="utf-8")
    retry = Path(".github/workflows/retry_failed_transcripts.yml").read_text(encoding="utf-8")
    for text in (workflow, retry):
        assert "space.bilibili.com/280534030/video" in text
        assert "BILIBILI_SOURCE_COOKIE_FILE_280534030" in text
        assert "BILIBILI_SOURCE_COOKIE_FILE_ZHANG_XUEFENG" not in text


def test_script_defaults_to_target_space_and_optional_cookie():
    script = Path("scripts/transcribe_bili.py").read_text(encoding="utf-8")
    assert "https://space.bilibili.com/280534030/video" in script
    assert "no cookie file supplied; public videos only" in script
    assert '"/lists/"' in script


def test_bilibili_json_cookie_export_is_converted_without_leaking_values():
    from prepare_bilibili_cookies import convert

    output = convert(
        '{"cookie_info":{"domains":[".bilibili.com"],"cookies":['
        '{"name":"SESSDATA","value":"secret-value","expires":1801216602,"secure":0}'
        ']}}'
    )
    assert "SESSDATA" in output
    assert "secret-value" in output
    assert output.startswith("# Netscape HTTP Cookie File")


def test_bilibili_cookie_conversion_rejects_non_bilibili_domains():
    from prepare_bilibili_cookies import convert

    with pytest.raises(ValueError, match="no usable Bilibili cookies"):
        convert('{"cookies":[{"name":"x","value":"y","domain":".example.com"}]}')


def test_collection_entries_are_recursive_and_deduplicated(monkeypatch):
    collections = {
        "https://space.bilibili.com/280534030/lists/10?type=season": {
            "entries": [
                {"id": "BV1CHILD", "title": "child"},
                {"id": "BV1ROOT", "title": "duplicate"},
            ]
        }
    }

    def fake_fetch(url):
        return collections[url]

    monkeypatch.setattr(transcribe_bili, "fetch_playlist_json", fake_fetch)
    data = {
        "entries": [
            {"id": "BV1ROOT", "title": "root"},
            {"url": "https://space.bilibili.com/280534030/lists/10?type=season"},
        ]
    }
    queue = transcribe_bili.collect_video_entries(data)
    assert [item["id"] for item in queue] == ["BV1ROOT", "BV1CHILD"]
    assert all(item["url"].startswith("https://www.bilibili.com/video/BV") for item in queue)
