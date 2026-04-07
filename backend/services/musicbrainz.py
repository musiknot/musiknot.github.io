import musicbrainzngs

musicbrainzngs.set_useragent("MusiknotApp", "1.0", "contact@musiknot.com")


def normalize_artist_name(name: str) -> str:
    """
    "Yonezu, Kenshi" → "Kenshi Yonezu" 로 변환.
    쉼표가 없는 경우 그대로 반환.
    """
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        return f"{parts[1]} {parts[0]}"
    return name


def clean_title(title: str) -> str:
    """
    부제 패턴 제거.
    예: "Sayonara, Mata Itsuka! - Sayonara" → "Sayonara, Mata Itsuka!"
        "Ama no Jaku (TV Size)"             → "Ama no Jaku"
    """
    import re
    title = re.sub(r'\s*-\s*\S+.*$', '', title).strip()
    title = re.sub(r'\s*\(.*?\)\s*$', '', title).strip()
    return title


def get_english_candidates(title: str, artist: str) -> list[dict]:
    """
    MusicBrainz에서 영어 제목 후보를 모두 수집해서 리스트로 반환.
    예: [
        {"english_title": "Martian",  "english_artist": "Yorushika"},
        {"english_title": "Kaseijin", "english_artist": "Yorushika"},
    ]
    """
    try:
        result = musicbrainzngs.search_recordings(
            recording=title,
            artist=artist,
            limit=5
        )
    except musicbrainzngs.WebServiceError as e:
        print(f"[MusicBrainz] WebServiceError: {e}")
        return []

    for rec in result.get("recording-list", []):
        print(f"[MusicBrainz] video={rec.get('video')}, score={rec.get('ext:score')}, title={rec.get('title')}")

        # 뮤직비디오 제외
        if rec.get("video") == "true":
            print("[MusicBrainz] → 뮤직비디오라 제외")
            continue
        # 유사도 70% 미만 제외
        if int(rec.get("ext:score", 0)) < 70:
            print("[MusicBrainz] → score 70 미만이라 제외")
            continue

        artist_info = rec.get("artist-credit", [{}])[0].get("artist", {})

        # 영어 아티스트명: sort-name 뒤집기 우선 적용
        en_artist = normalize_artist_name(artist_info.get("sort-name", ""))
        print(f"[MusicBrainz] sort-name 기반 아티스트: {en_artist}")

        # locale=en alias가 있으면 덮어씌움
        for alias in artist_info.get("alias-list", []):
            print(f"[MusicBrainz] alias 확인: locale={alias.get('locale')}, primary={alias.get('primary')}, name={alias.get('name')}")
            if alias.get("locale") == "en" and alias.get("primary") == "primary":
                en_artist = alias.get("name", en_artist)
                print(f"[MusicBrainz] → locale=en alias 발견: {en_artist}")
                break

        # 영어 제목 후보 수집 (원본 + 정제본)
        seen_titles = set()
        candidates  = []

        for release in rec.get("release-list", []):
            status = release.get("status", "")
            disam  = release.get("disambiguation", "")
            is_en  = (
                status == "Pseudo-Release" or
                "北米" in disam or
                release.get("artist-credit", [{}])[0]
                       .get("name", "").isascii()
            )
            if is_en:
                try:
                    track_title = (
                        release["medium-list"][0]["track-list"][0]["title"]
                    )
                    if track_title.isascii() and track_title not in seen_titles:
                        seen_titles.add(track_title)
                        candidates.append({
                            "english_title":  track_title,
                            "english_artist": en_artist
                        })
                        print(f"[MusicBrainz] → 후보 추가 (원본): {track_title}")

                        # 정제본이 원본과 다를 경우 추가 후보로 등록
                        cleaned = clean_title(track_title)
                        if cleaned != track_title and cleaned not in seen_titles:
                            seen_titles.add(cleaned)
                            candidates.append({
                                "english_title":  cleaned,
                                "english_artist": en_artist
                            })
                            print(f"[MusicBrainz] → 후보 추가 (정제본): {cleaned}")

                except (KeyError, IndexError):
                    pass

        if candidates:
            return candidates

        print("[MusicBrainz] → 영어 제목 없음")
        return []

    print("[MusicBrainz] → 결과 없음")
    return []