import requests
from bs4 import BeautifulSoup

MELON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}

if __name__ == "__main__":
    res = requests.get(
        "https://www.melon.com/search/song/index.htm",
        params={"q": "SWIM BTS"},
        headers=MELON_HEADERS,
        timeout=10
    )
    doc = BeautifulSoup(res.text, "html.parser")

    for row in doc.select("tr"):
        btn = row.select_one("button[data-song-no]")
        if not btn:
            continue
        found_id  = btn.get("data-song-no")
        title_el  = row.select_one("a.fc_gray[title]")
        artist_el = row.select_one("a.fc_mgray")
        print(f"songNo={found_id}, title={title_el.text.strip() if title_el else None}, artist={artist_el.text.strip() if artist_el else None}")