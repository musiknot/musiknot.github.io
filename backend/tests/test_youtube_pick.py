"""YouTube 검색 결과에서 MV / Topic 을 골라내는 로직.

`search.list` 는 호출당 100 유닛이고 기본 할당량이 10,000/일이다. 예전에는
MV 용과 Topic 용으로 두 번 검색해서 하루 50 파싱이 상한이었다. 검색을 한 번만
하고 결과 목록에서 둘 다 골라내면 상한이 100 파싱으로 두 배가 된다.

고르는 로직을 순수 함수로 떼어냈기 때문에 API 키 없이, 네트워크 없이 검증된다.
"""
from __future__ import annotations

import pytest

from services.youtube import pick_mv_and_topic


def item(video_id: str | None, title: str, channel: str) -> dict:
    """search.list 응답 항목 한 개의 모양."""
    return {
        "id": {"videoId": video_id} if video_id else {"kind": "youtube#channel"},
        "snippet": {"title": title, "channelTitle": channel},
    }


CASES = [
    (
        "MV 표지와 Topic 이 모두 있으면 각각 고른다",
        [item("aaa", "[MV] 아이유 - 밤편지", "1theK"),
         item("bbb", "밤편지", "아이유 - Topic")],
        "aaa", "bbb",
    ),
    (
        "Topic 이 앞에 와도 MV 는 뒤에서 찾는다",
        [item("ttt", "밤편지", "IU - Topic"),
         item("mmm", "IU(아이유) _ Through the Night(밤편지) MV", "1theK")],
        "mmm", "ttt",
    ),
    (
        "MV 표지가 없으면 Topic 이 아닌 첫 항목",
        [item("x1", "밤편지 커버", "누군가"),
         item("x2", "밤편지 lyrics", "가사채널")],
        "x1", None,
    ),
    (
        "Topic 만 있으면 MV 는 없다",
        [item("only", "밤편지", "아이유 - Topic")],
        None, "only",
    ),
    (
        "한국어 표지 '뮤직비디오' 도 인식한다",
        [item("k1", "아무 영상", "채널A"),
         item("k2", "아이유 밤편지 뮤직비디오", "채널B")],
        "k2", None,
    ),
    (
        "videoId 가 없는 채널/재생목록 결과는 건너뛴다",
        [item(None, "아이유 채널", "IU"),
         item("real", "밤편지", "1theK")],
        "real", None,
    ),
    ("빈 결과", [], None, None),
    ("None 입력", None, None, None),
]


@pytest.mark.parametrize("name,items,exp_mv,exp_topic", CASES,
                         ids=[c[0] for c in CASES])
def test_pick(name, items, exp_mv, exp_topic):
    mv, topic = pick_mv_and_topic(items)
    assert (mv.track_id if mv else None) == exp_mv
    assert (topic.track_id if topic else None) == exp_topic


def test_alive_is_not_read_as_live():
    """ASCII 표지는 단어 경계로 매칭해야 한다.

    'Alive' 안의 'live' 를 라이브 음원으로 읽으면 안 된다. scoring.py 의 변형
    표지 판정이 같은 이유로 단어 경계를 쓰는데, 여기서도 같은 함정이 있다.
    """
    mv, _ = pick_mv_and_topic([item("a", "Alive", "채널")])
    assert mv is not None and mv.track_id == "a"


def test_topic_channel_never_becomes_mv():
    """Topic 채널은 자동 생성 음원이라 MV 자리에 오면 안 된다."""
    mv, topic = pick_mv_and_topic([item("t", "밤편지 M/V", "아이유 - Topic")])
    assert mv is None
    assert topic is not None and topic.track_id == "t"
