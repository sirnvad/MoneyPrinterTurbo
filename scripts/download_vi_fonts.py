"""
Download 50 popular Google Fonts that support Vietnamese for subtitle use.
Saves .ttf files to resource/fonts/
"""
import os
import re
import sys
import requests

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "resource", "fonts")
os.makedirs(FONT_DIR, exist_ok=True)

# 50 popular Google Fonts with Vietnamese support, with preferred weights
FONTS = [
    ("Roboto", "700"),
    ("Open Sans", "700"),
    ("Montserrat", "700"),
    ("Lato", "700"),
    ("Poppins", "700"),
    ("Noto Sans", "700"),
    ("Raleway", "700"),
    ("Nunito", "700"),
    ("Ubuntu", "700"),
    ("Oswald", "700"),
    ("Source Sans 3", "700"),
    ("Merriweather", "700"),
    ("PT Sans", "700"),
    ("Cabin", "700"),
    ("Barlow", "700"),
    ("Exo 2", "700"),
    ("Fira Sans", "700"),
    ("Work Sans", "700"),
    ("Quicksand", "700"),
    ("Mulish", "700"),
    ("Karla", "700"),
    ("Inter", "700"),
    ("DM Sans", "700"),
    ("Manrope", "700"),
    ("Outfit", "700"),
    ("Rubik", "700"),
    ("Josefin Sans", "700"),
    ("Titillium Web", "700"),
    ("Encode Sans", "700"),
    ("Libre Franklin", "700"),
    ("Public Sans", "700"),
    ("Lexend", "700"),
    ("Plus Jakarta Sans", "700"),
    ("Comfortaa", "700"),
    ("Dosis", "700"),
    ("Oxygen", "700"),
    ("Cantarell", "700"),
    ("IBM Plex Sans", "700"),
    ("Arimo", "700"),
    ("Cairo", "700"),
    ("Signika", "700"),
    ("Yanone Kaffeesatz", "700"),
    ("Archivo", "700"),
    ("Archivo Black", "400"),
    ("Be Vietnam Pro", "700"),
    ("Noto Serif", "700"),
    ("Crimson Text", "700"),
    ("Zilla Slab", "700"),
    ("Overpass", "700"),
    ("Nunito Sans", "700"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_font_url(family: str, weight: str) -> str | None:
    css_url = (
        f"https://fonts.googleapis.com/css2?family="
        f"{family.replace(' ', '+')}:wght@{weight}&display=swap&subset=vietnamese"
    )
    resp = requests.get(css_url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        return None
    # Pick the last latin/vietnamese src url (ttf or woff2 fallback)
    urls = re.findall(r"src: url\((https://[^)]+\.(?:ttf|woff2))\)", resp.text)
    # Prefer .ttf; fall back to .woff2
    ttf = [u for u in urls if u.endswith(".ttf")]
    return (ttf or urls or [None])[-1]


def download_font(family: str, weight: str) -> bool:
    safe_name = family.replace(" ", "") + f"-{weight}.ttf"
    dest = os.path.join(FONT_DIR, safe_name)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"  skip (exists): {safe_name}")
        return True

    url = fetch_font_url(family, weight)
    if not url:
        print(f"  FAILED (no url): {family}")
        return False

    # Google Fonts CSS2 returns woff2 by default for Chrome UA;
    # re-fetch with a UA that gets ttf
    if url.endswith(".woff2"):
        # try direct ttf variant by changing the UA
        ttf_headers = dict(HEADERS)
        ttf_headers["User-Agent"] = (
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        )
        css_url = (
            f"https://fonts.googleapis.com/css?family="
            f"{family.replace(' ', '+')}:{weight}&subset=vietnamese"
        )
        resp = requests.get(css_url, headers=ttf_headers, timeout=15)
        urls = re.findall(r"url\((https://[^)]+\.ttf)\)", resp.text)
        url = urls[-1] if urls else url

    ext = ".woff2" if url.endswith(".woff2") else ".ttf"
    dest = os.path.join(FONT_DIR, family.replace(" ", "") + f"-{weight}{ext}")

    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code != 200 or len(r.content) < 1000:
        print(f"  FAILED (download error {r.status_code}): {family}")
        return False

    with open(dest, "wb") as f:
        f.write(r.content)
    print(f"  OK: {os.path.basename(dest)} ({len(r.content)//1024} KB)")
    return True


def main():
    print(f"Saving fonts to: {os.path.abspath(FONT_DIR)}\n")
    ok = fail = 0
    for i, (family, weight) in enumerate(FONTS, 1):
        print(f"[{i:02d}/{len(FONTS)}] {family} w{weight}")
        if download_font(family, weight):
            ok += 1
        else:
            fail += 1
    print(f"\nDone: {ok} downloaded, {fail} failed.")


if __name__ == "__main__":
    main()
