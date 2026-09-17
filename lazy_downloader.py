#!/opt/homebrew/bin/python3
import subprocess, threading, tkinter as tk
from pathlib import Path

def find_ytdlp():
    for p in ["/opt/homebrew/bin/yt-dlp", "/usr/local/bin/yt-dlp"]:
        if Path(p).exists(): return p
    return None

def parse_time(s):
    """'90' (secs), '1:30' (m:s) or '0:01:30.5' (h:m:s) -> seconds. None if not a time."""
    s = (s or "").strip()
    if not s: return None
    parts = s.split(":")
    if len(parts) > 3: return None
    vals = []
    for p in parts:
        p = p.strip()
        if not p: return None
        try:
            vals.append(float(p))
        except ValueError:
            return None
    if any(v < 0 for v in vals): return None
    # fields after the first are sexagesimal (0-59) — anything bigger is a typo
    if any(v >= 60 for v in vals[1:]): return None
    total = 0.0
    for v in vals:
        total = total * 60 + v
    return total

def fmt_secs(s):
    """Seconds -> 'h:mm:ss' (fractional tenths kept when the cut is not whole)."""
    s = max(0.0, float(s))
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s - h * 3600 - m * 60
    if abs(sec - round(sec)) < 0.05:
        sec = int(round(sec))
        if sec == 60: m += 1; sec = 0
        if m == 60: h += 1; m = 0
        return "%d:%02d:%02d" % (h, m, sec)
    return "%d:%02d:%04.1f" % (h, m, sec)

# ─ Phosphor green-on-black palette ──
BG   = "#000000"   # pure black
FG   = "#00FF00"   # bright phosphor green
ACC  = "#00FF00"   # title (same green)
SUCC = "#00FF00"   # success in green
ERR  = "#FF5555"   # errors in red (terminal convention)
BORD = "#00CC00"   # slightly dimmer green for the = borders
MUT  = "#008800"   # muted green

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LAZY DOWNLOADER")
        self.root.geometry("680x520")
        self.root.minsize(500, 360)
        self.root.configure(bg=BG)

        self.ytdlp = find_ytdlp()
        self.dldir = str(Path.home() / "Desktop")

        self.mode = "menu"
        self.dltype = None
        self.input_text = ""
        self.url = ""            # URL held between the clip prompts
        self.clip_start = None   # seconds, or None
        self.clip_end = None     # seconds, or None
        self._cursor = True
        self._lines = []
        self._prompt = "Pick: "
        self._base = "Pick: "    # prompt text without the typed input

        self.c = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.c.pack(fill="both", expand=True)

        self.root.bind("<Key>", self._on_key)
        self.root.bind("<Configure>", lambda e: self._redraw())
        # Paste: right-click, ctrl-click (trackpad), middle-click, and ⌘V
        self.root.bind("<Button-2>", self._paste)
        self.root.bind("<Button-3>", self._paste)
        self.root.bind("<Control-Button-1>", self._paste)
        self.root.bind("<Command-v>", self._paste)
        self.root.bind("<Command-V>", self._paste)
        self.root.after(100, self._boot)

    def _boot(self):
        self._lines = [
            ("", FG),
            ("=" * 40, BORD),
            ("       LAZY  DOWNLOADER  v1.1", ACC),
            ("=" * 40, BORD),
            ("", FG),
            (" [1]  Video download          (yt-dlp)", FG),
            (" [2]  Audio download          (yt-dlp)", FG),
            (" [3]  Video CLIP download     (start/end)", FG),
            ("", FG),
            (" [U]  Update yt-dlp", FG),
            (" [Q]  Quit", FG),
            ("", FG),
            ("-" * 40, BORD),
        ]
        self._set_prompt("Pick: ")
        self._redraw()
        self._blink()

    def _blink(self):
        self._cursor = not self._cursor
        self._redraw()
        self.root.after(530, self._blink)

    def _redraw(self):
        self.c.delete("all")
        y = 16
        for text, color in self._lines:
            self.c.create_text(18, y, text=text, fill=color,
                               font=("Courier", 13), anchor="nw")
            y += 22

        # Separator line
        y += 4
        cur = "\u2588" if self._cursor and self.mode != "busy" else " "
        self.c.create_text(18, y, text=self._prompt + cur, fill=FG,
                           font=("Courier", 14), anchor="nw")

    def _on_key(self, ev):
        if self.mode == "menu":
            self._menu_key(ev)
        elif self.mode == "url":
            self._url_key(ev)
        elif self.mode in ("clip_start", "clip_end"):
            self._clip_key(ev)

    def _menu_key(self, ev):
        c = ev.char.upper() if ev.char else ""
        if c == "1":
            self.mode = "url"; self.dltype = "video"
            self.input_text = ""
            self._set_prompt("Paste video URL: ")
        elif c == "2":
            self.mode = "url"; self.dltype = "audio"
            self.input_text = ""
            self._set_prompt("Paste audio URL: ")
        elif c == "3":
            self.mode = "url"; self.dltype = "clip"
            self.input_text = ""; self.clip_start = None; self.clip_end = None
            self._set_prompt("Paste video URL to clip: ")
        elif c == "U": self._update()
        elif c == "Q": self.root.destroy()

    def _url_key(self, ev):
        if ev.keysym == "Return":
            if not self.input_text.strip():
                self._redraw(); return
            if self.dltype == "clip":
                self.url = self.input_text.strip()
                self.input_text = ""
                self.mode = "clip_start"
                self._set_prompt("Clip START (mm:ss / h:mm:ss, ENTER = 0:00): ")
            else:
                self._download()
        elif ev.keysym == "Escape":
            self._to_menu()
        elif ev.keysym == "BackSpace":
            self.input_text = self.input_text[:-1]
            self._set_prompt(self._base)
        elif ev.char and len(ev.char) == 1:
            self.input_text += ev.char
            self._set_prompt(self._base)
        self._redraw()

    def _clip_key(self, ev):
        if ev.keysym == "Return":
            raw = self.input_text.strip()
            t = parse_time(raw)
            if raw and t is None:
                self._flash("  ? bad time \u2014 use 90, 1:30 or 0:01:30", ERR)
                self._redraw(); return
            if self.mode == "clip_start":
                self.clip_start = 0.0 if t is None else t
                self.input_text = ""
                self.mode = "clip_end"
                self._set_prompt("Clip END (mm:ss / h:mm:ss, ENTER = to end): ")
            else:
                self.clip_end = t
                if self.clip_end is not None and self.clip_end <= (self.clip_start or 0.0):
                    self._flash("  ? END must be after START", ERR)
                    self._redraw(); return
                self._download()
        elif ev.keysym == "Escape":
            self._to_menu()
        elif ev.keysym == "BackSpace":
            self.input_text = self.input_text[:-1]
            self._set_prompt(self._base)
        elif ev.char and len(ev.char) == 1:
            self.input_text += ev.char
            self._set_prompt(self._base)
        self._redraw()

    def _set_prompt(self, base):
        self._base = base
        self._prompt = base + self.input_text

    def _to_menu(self):
        self.mode = "menu"; self.dltype = None
        self.input_text = ""; self.url = ""
        self.clip_start = None; self.clip_end = None
        self._set_prompt("Pick: ")

    def _flash(self, msg, color):
        self._lines.append((msg, color))

    def _paste(self, ev=None):
        if self.mode not in ("url", "clip_start", "clip_end"):
            return
        try:
            self.input_text = self.root.clipboard_get().strip()
            self._set_prompt(self._base)
            self._redraw()
        except tk.TclError:
            pass

    def _download(self):
        # in the clip flow input_text holds the END time by now, so use the saved URL
        url = self.url if self.dltype == "clip" else self.input_text.strip()
        if not url: return
        self.url = url
        self.input_text = ""
        self.mode = "busy"
        if self.dltype == "clip":
            self._lines.append(("  CLIP %s \u2192 %s" % (
                fmt_secs(self.clip_start),
                "END of video" if self.clip_end is None else fmt_secs(self.clip_end)), MUT))
        self._set_prompt("Downloading...")
        self._redraw()
        threading.Thread(target=self._run_dl, args=(url,), daemon=True).start()

    def _run_dl(self, url):
        if self.dltype == "clip":
            start = self.clip_start or 0.0
            end = self.clip_end
            # yt-dlp takes seconds; "inf" means "to the end of the video"
            rng = "%g-%s" % (start, "inf" if end is None else "%g" % end)
            tag = fmt_secs(start).replace(":", "-") + "_" + (
                "end" if end is None else fmt_secs(end).replace(":", "-"))
            out = str(Path(self.dldir) / ("%(title)s [clip " + tag + "].%(ext)s"))
            cmd = [self.ytdlp, "-f",
                   "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                   "--download-sections", "*" + rng,
                   "--force-keyframes-at-cuts",
                   "-o", out, url]
        elif self.dltype == "audio":
            out = str(Path(self.dldir) / "%(title)s.%(ext)s")
            cmd = [self.ytdlp, "-x", "--audio-format", "mp3", "-o", out, url]
        else:
            out = str(Path(self.dldir) / "%(title)s.%(ext)s")
            cmd = [self.ytdlp, "-f",
                   "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                   "-o", out, url]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            self.root.after(0, self._done, "  TIMEOUT", ERR); return
        except Exception as e:
            self.root.after(0, self._done, "  ERROR: " + str(e), ERR); return
        if r.returncode == 0:
            self.root.after(0, self._done, "  OK \u2192 " + self.dldir, SUCC)
        else:
            ls = [l for l in r.stderr.splitlines() if l.strip()]
            err = ls[-1] if ls else r.stderr.strip() or "Unknown"
            self.root.after(0, self._done, "  FAILED: " + err, ERR)

    def _done(self, msg, color):
        self._lines.append((msg, color))
        self._to_menu()
        self._redraw()

    def _update(self):
        self.mode = "busy"
        self.input_text = ""
        self._set_prompt("Updating yt-dlp via Homebrew...")
        self._redraw()
        threading.Thread(target=self._run_update, daemon=True).start()

    def _run_update(self):
        try:
            r = subprocess.run(["brew", "upgrade", "yt-dlp"],
                              capture_output=True, text=True, timeout=300)
        except Exception as e:
            self.root.after(0, self._up_done, "  ERROR: " + str(e), ERR); return
        if r.returncode == 0:
            self.ytdlp = find_ytdlp()
            ver = ""
            for l in r.stdout.splitlines():
                if "yt-dlp" in l and "->" in l: ver = l.strip()
            self.root.after(0, self._up_done, "  " + (ver if ver else "yt-dlp up to date."), SUCC)
        else:
            err = r.stderr.strip() or "Unknown"
            self.root.after(0, self._up_done, "  FAILED: " + err, ERR)

    def _up_done(self, msg, color):
        self._lines.append((msg, color))
        self._to_menu()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    App().run()
