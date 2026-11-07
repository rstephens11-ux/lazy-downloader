"""Save a tweet (text + photos + videos) into a plain folder on this Mac.

Uses the free, public FxTwitter API (api.fxtwitter.com — the service behind the
"fxtwitter" link previews). No X login, no API key, no cost. It is unofficial, so it
could break one day; that is exactly why each tweet is saved as a full local copy
instead of a bookmark.

Each tweet becomes one folder:

    ~/Saved Tweets/2014-03-03 @TheEllenShow - If only Bradley's arm was longer/
        2014-03-03 @TheEllenShow - If only Bradley's arm was longer.md   <- text, searchable
        photo-1.jpg
        .tweet-440322224407314432.json                                   <- raw data (hidden)

The .md is named like its folder so Spotlight / Finder search results are readable.
The hidden .json holds everything the API returned and doubles as the "already
saved?" marker.
"""
import datetime as _dt
import json
import os
import re
import shutil
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.fxtwitter.com/2/status/"
UA = "LazyDownloader/1.4 (personal tweet archiver)"
DEFAULT_DIR = Path.home() / "Saved Tweets"
VIDEO_MAX_BITRATE = 2_200_000        # ~720p: plenty to rewatch, keeps files small
MAX_FILE_BYTES = 400 * 1024 * 1024   # skip (and note) any single file bigger than this
TITLE_CHARS = 60


class SaveError(Exception):
    """A problem worth showing the user as-is."""


# ── network ──────────────────────────────────────────────────────────────

def _ssl_ctx():
    """A bundled .app can lose track of the system certificates; fall back to
    macOS's own bundle so HTTPS keeps working."""
    ctx = ssl.create_default_context()
    if not ctx.cert_store_stats().get("x509_ca"):
        for f in ("/etc/ssl/cert.pem", "/opt/homebrew/etc/openssl@3/cert.pem"):
            if os.path.exists(f):
                ctx.load_verify_locations(f)
                break
    return ctx


_CTX = None


def _open(url, timeout=30):
    global _CTX
    if _CTX is None:
        _CTX = _ssl_ctx()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout, context=_CTX)


def tweet_id_from(text):
    """Pull the numeric ID out of anything that looks like a tweet link (x.com,
    twitter.com, fxtwitter, vxtwitter, fixupx, /photo/1 tails, ?s=20 junk) or a
    bare ID. None if there isn't one."""
    s = (text or "").strip()
    if re.fullmatch(r"\d{1,20}", s):
        return s
    m = re.search(r"/status(?:es)?/(\d{1,20})", s)
    return m.group(1) if m else None


def fetch_tweet(tid) -> dict:
    data: dict
    try:
        with _open(API + tid) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8"))
        except Exception:
            data = {"code": e.code}
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        reason = getattr(e, "reason", e)
        raise SaveError("couldn't reach FxTwitter (%s) - online?" % reason)
    code = data.get("code")
    status = data.get("status")
    if code == 404 or (code == 200 and not status):
        raise SaveError("tweet not found - deleted, private, or a bad link")
    if code == 401:
        raise SaveError("that account is private - can't read it")
    if code != 200 or not isinstance(status, dict):
        raise SaveError("FxTwitter said %s: %s" % (code, data.get("message") or "error"))
    return data


def _download(url, dest):
    """Stream url -> dest. Returns bytes written. Raises SaveError past the cap."""
    tmp = dest.with_name(dest.name + ".part")
    total = 0
    with _open(url, timeout=60) as r:
        size = int(r.headers.get("Content-Length") or 0)
        if size > MAX_FILE_BYTES:
            raise SaveError("too big (%d MB)" % (size // 2**20))
        with open(tmp, "wb") as f:
            while True:
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_FILE_BYTES:
                    raise SaveError("too big (over %d MB)" % (MAX_FILE_BYTES // 2**20))
                f.write(chunk)
    if total == 0:
        tmp.unlink(missing_ok=True)
        raise SaveError("empty file")
    tmp.rename(dest)
    return total


# ── formatting ───────────────────────────────────────────────────────────

def _local(ts):
    return _dt.datetime.fromtimestamp(ts).astimezone() if ts else None


def _fmt_when(ts):
    d = _local(ts)
    return d.strftime("%Y-%m-%d %H:%M %Z") if d else "unknown date"


def _num(n):
    return "{:,}".format(n) if isinstance(n, (int, float)) else "?"


def _fmt_dur(secs):
    try:
        secs = int(round(float(secs)))
    except (TypeError, ValueError):
        return ""
    return "%d:%02d" % (secs // 60, secs % 60)


def make_title(status):
    """'2014-03-03 @TheEllenShow - If only Bradley's arm was longer' — safe as a
    folder AND file name."""
    d = _local(status.get("created_timestamp"))
    date = d.strftime("%Y-%m-%d") if d else "undated"
    handle = (status.get("author") or {}).get("screen_name") or "unknown"
    text = status.get("text") or ""
    text = re.sub(r"https?://\S+", "", text)            # links make bad titles
    text = re.sub(r"^(?:\s*@\w+)+\s*", "", text)        # reply's leading @mentions
    text = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", " ", text)  # filename-hostile chars
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        media = (status.get("media") or {}).get("all") or []
        text = "video" if any(m.get("type") != "photo" for m in media) else (
            "photo" if media else "tweet")
    if len(text) > TITLE_CHARS:
        cut = text[:TITLE_CHARS]
        text = (cut.rsplit(" ", 1)[0] if " " in cut[20:] else cut).rstrip() + "…"
    text = text.strip(" .")  # macOS dislikes names ending in a dot
    return "%s @%s - %s" % (date, handle, text)


def _pick_video_url(item):
    """Best mp4 at or under ~720p bitrate; else the smallest mp4; else whatever."""
    mp4s = [f for f in item.get("formats") or []
            if f.get("container") == "mp4" and f.get("url") and f.get("bitrate")]
    ok = [f for f in mp4s if f["bitrate"] <= VIDEO_MAX_BITRATE]
    if ok:
        return max(ok, key=lambda f: f["bitrate"])["url"]
    if mp4s:
        return min(mp4s, key=lambda f: f["bitrate"])["url"]
    return item.get("url")


def _media_plan(status, prefix=""):
    """[(filename, url, kind, item)] for every photo/video/gif in the tweet."""
    plan = []
    counts = {"photo": 0, "video": 0}
    for item in (status.get("media") or {}).get("all") or []:
        kind = "photo" if item.get("type") == "photo" else "video"
        url = item.get("url") if kind == "photo" else _pick_video_url(item)
        if not url:
            continue
        counts[kind] += 1
        ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower() or (
            ".jpg" if kind == "photo" else ".mp4")
        plan.append(("%s%s-%d%s" % (prefix, kind, counts[kind], ext), url, kind, item))
    return plan


def _media_md(plan, results):
    out = []
    for fname, url, kind, item in plan:
        err = results.get(fname)
        if kind == "photo":
            out.append(("![%s](%s)" % (fname, fname)) if not err else
                       "_(photo not saved: %s — %s)_" % (err, url))
        else:
            dur = _fmt_dur(item.get("duration"))
            label = "%s%s" % (fname, " (%s)" % dur if dur else "")
            out.append(("[▶ %s](%s)" % (label, fname)) if not err else
                       "_(video not saved: %s — %s)_" % (err, url))
        alt = item.get("altText") or item.get("alt_text")
        if alt:
            out.append("> Alt text: " + alt.replace("\n", " "))
        out.append("")
    return out


def _extras_md(status):
    """Poll, link card, X article and community note — all searchable text."""
    out = []
    poll = status.get("poll")
    if isinstance(poll, dict) and poll.get("choices"):
        out.append("**Poll** (%s votes)" % _num(poll.get("total_votes")))
        for c in poll["choices"]:
            out.append("- %s — %s%% (%s)" % (c.get("label"), c.get("percentage"), _num(c.get("count"))))
        out.append("")
    card = status.get("card")
    if isinstance(card, dict) and card.get("url"):
        title = card.get("title") or card.get("domain") or "link"
        out.append("**Link:** [%s](%s)" % (title, card["url"]))
        if card.get("description"):
            out.append("> " + card["description"].replace("\n", " "))
        out.append("")
    art = status.get("article")
    if isinstance(art, dict) and (art.get("title") or art.get("content")):
        out.append("## Article: %s" % (art.get("title") or "untitled"))
        blocks = ((art.get("content") or {}).get("blocks") or [])
        body = [b.get("text", "") for b in blocks if isinstance(b, dict)]
        body = [t for t in body if t.strip()] or [art.get("preview_text") or ""]
        out += body + [""]
    note = status.get("community_note")
    if isinstance(note, dict) and note.get("text"):
        out.append("**Community note:** " + note["text"].replace("\n", " "))
        out.append("")
    return out


def build_markdown(status, title, results, plan_main, plan_quote, saved_at):
    a = status.get("author") or {}
    handle = a.get("screen_name") or "unknown"
    when = _fmt_when(status.get("created_timestamp"))
    url = status.get("url") or "https://x.com/i/status/%s" % status.get("id")

    def q(s):
        return json.dumps(s or "", ensure_ascii=False)

    md = [
        "---",
        "tweet_id: %s" % q(status.get("id")),
        "author: %s" % q("@" + handle),
        "author_name: %s" % q(a.get("name")),
        "posted: %s" % q(when),
        "saved: %s" % q(saved_at),
        "url: %s" % q(url),
        "---",
        "",
        "# %s" % title,
        "",
        "**%s** (@%s) · %s" % (a.get("name") or handle, handle, when),
    ]
    rt = status.get("replying_to")
    if isinstance(rt, dict) and rt.get("screen_name"):
        md.append("Replying to @%s%s" % (rt["screen_name"],
                                        " — " + rt["url"] if rt.get("url") else ""))
    md += ["", status.get("text") or "", ""]
    md += _media_md(plan_main, results)
    md += _extras_md(status)

    quote = status.get("quote")
    if isinstance(quote, dict):
        if quote.get("text") is not None and quote.get("author"):
            qa = quote["author"]
            md += ["## Quoting %s (@%s) · %s" % (qa.get("name") or "", qa.get("screen_name"),
                                                 _fmt_when(quote.get("created_timestamp"))),
                   ""]
            md += ["> " + line for line in (quote.get("text") or "").split("\n")]
            md.append("")
            md += _media_md(plan_quote, results)
            md += _extras_md(quote)
            if quote.get("url"):
                md += ["Quoted post: " + quote["url"], ""]
        else:
            md += ["_(Quoted a post that is no longer available.)_", ""]

    counts = ["%s %s" % (_num(status.get(k)), k) for k in ("replies", "reposts", "likes", "views")
              if isinstance(status.get(k), (int, float))]  # old tweets have no view count
    md += ["---"]
    if counts:
        md.append("%s (as of %s)" % (" · ".join(counts), saved_at))
    md += ["", "Original: " + url, ""]
    return "\n".join(md)


# ── the one call the app makes ───────────────────────────────────────────

def already_saved(tid, root):
    hits = list(Path(root).glob("*/.tweet-%s.json" % tid))
    return hits[0].parent if hits else None


def save_tweet(text, root=DEFAULT_DIR):
    """Save the tweet in `text` (a link or an ID) under `root`.

    Returns a dict: {"status": "saved" | "already", "folder": Path, "photos": n,
    "videos": n, "failed": [(filename, reason)]}. Raises SaveError for problems the
    user should see verbatim.
    """
    tid = tweet_id_from(text)
    if not tid:
        raise SaveError("that doesn't look like a tweet link")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    prior = already_saved(tid, root)
    if prior:
        return {"status": "already", "folder": prior, "photos": 0, "videos": 0, "failed": []}

    data = fetch_tweet(tid)
    status = data["status"]
    title = make_title(status)
    saved_at = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")

    # Build in a hidden scratch folder, rename into place at the end — a crash or a
    # dead network never leaves a half-saved tweet that looks "already saved".
    work = root / (".partial-%s" % tid)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()
    try:
        plan_main = _media_plan(status)
        q = status.get("quote")
        quote = q if isinstance(q, dict) else {}
        plan_quote = _media_plan(quote, prefix="quoted-") if quote.get("author") else []
        results, failed, n = {}, [], {"photo": 0, "video": 0}
        for fname, url, kind, _item in plan_main + plan_quote:
            try:
                _download(url, work / fname)
                n[kind] += 1
            except SaveError as e:
                results[fname] = str(e); failed.append((fname, str(e)))
            except Exception as e:  # one bad image must not sink the whole save
                results[fname] = type(e).__name__; failed.append((fname, type(e).__name__))

        md = build_markdown(status, title, results, plan_main, plan_quote, saved_at)
        (work / (title + ".md")).write_text(md, encoding="utf-8")
        (work / (".tweet-%s.json" % tid)).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        final = root / title
        k = 2
        while final.exists():
            final = root / ("%s (%d)" % (title, k)); k += 1
        if final.name != title:  # keep the .md named like its folder
            (work / (title + ".md")).rename(work / (final.name + ".md"))
        work.rename(final)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    return {"status": "saved", "folder": final, "photos": n["photo"],
            "videos": n["video"], "failed": failed}


def main(argv):
    """Headless use / self-test of the bundled app:
        Lazy Downloader --save-tweet URL [--into DIR]"""
    i = argv.index("--save-tweet")
    url = argv[i + 1] if i + 1 < len(argv) else ""
    root = Path(argv[argv.index("--into") + 1]) if "--into" in argv else DEFAULT_DIR
    try:
        r = save_tweet(url, root)
    except SaveError as e:
        print("FAILED:", e)
        return 1
    print(json.dumps({k: (str(v) if isinstance(v, Path) else v) for k, v in r.items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv) if "--save-tweet" in sys.argv else 0)
