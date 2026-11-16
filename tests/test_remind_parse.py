"""提醒时间解析：内容与时间要干净分离。"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scheduler import next_run_from_text, parse_remind_when


def test_minute_suffix_is_part_of_time():
    """「13点20分」里的「分」属于时间，不该残留在提醒内容里。"""
    when, repeat = parse_remind_when("数学分析考试 明天下午13点20分")
    assert when == "明天下午13点20分"
    assert repeat == "none"
    content = "数学分析考试 明天下午13点20分".replace(when, "").strip()
    assert content == "数学分析考试"


def test_time_without_minute_suffix():
    when, _ = parse_remind_when("喝水 明天9点")
    assert when == "明天9点"


def test_next_run_uses_parsed_time():
    now = datetime(2026, 11, 14, 18, 50)
    when, _ = parse_remind_when("数学分析考试 明天下午13点20分")
    assert next_run_from_text(when, now) == datetime(2026, 11, 15, 13, 20)


def test_relative_days_and_weekdays():
    """后天、大后天、周X 都要能解析。"""
    from scheduler import next_run_from_text, parse_remind_when

    now = datetime(2026, 11, 16, 8, 15)  # 周一
    cases = {
        "交作业 后天下午3点": datetime(2026, 11, 18, 15, 0),
        "交作业 大后天9点": datetime(2026, 11, 19, 9, 0),
        "交作业 明天上午9点": datetime(2026, 11, 17, 9, 0),
        "交作业 周日下午3点": datetime(2026, 11, 22, 15, 0),
    }
    for raw, expected in cases.items():
        when, _ = parse_remind_when(raw)
        assert when, f"{raw} 未解析出时间"
        assert next_run_from_text(when, now) == expected, raw


def test_afternoon_and_evening_convert_to_24h():
    """下午/晚上/今晚 要换算成 24 小时制。"""
    from scheduler import next_run_from_text, parse_remind_when

    now = datetime(2026, 11, 16, 8, 15)
    cases = {
        "开会 明天下午3点": datetime(2026, 11, 17, 15, 0),
        "开会 晚上8点": datetime(2026, 11, 16, 20, 0),
        "开会 今晚8点": datetime(2026, 11, 16, 20, 0),
        "开会 明天中午12点": datetime(2026, 11, 17, 12, 0),
    }
    for raw, expected in cases.items():
        when, _ = parse_remind_when(raw)
        assert when, f"{raw} 未解析出时间"
        assert next_run_from_text(when, now) == expected, raw
