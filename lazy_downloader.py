#!/opt/homebrew/bin/python3
import subprocess, threading, tkinter as tk
from pathlib import Path

def find_ytdlp():
    for p in ["/opt/homebrew/bin/yt-dlp", "/usr/local/bin/yt-dlp"]:
        if Path(p).exists(): return p
    return None

# ── Phosphor green-on-black palette ──
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
        self._cursor = True
        self._lines = []
        self._prompt = "Pick: "

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
            ("       LAZY  DOWNLOADER  v1.0", ACC),
            ("=" * 40, BORD),
            ("", FG),
            (" [1]  Video download          (yt-dlp)", FG),
            (" [2]  Audio download          (yt-dlp)", FG),
            ("", FG),
            (" [U]  Update yt-dlp", FG),
            (" [Q]  Quit", FG),
            ("", FG),
            ("-" * 40, BORD),
        ]
        self._prompt = "Pick: "
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

    def _menu_key(self, ev):
        c = ev.char.upper() if ev.char else ""
        if c == "1":
            self.mode = "url"; self.dltype = "video"
            self.input_text = ""
            self._prompt = "Paste video URL: "
        elif c == "2":
            self.mode = "url"; self.dltype = "audio"
            self.input_text = ""
            self._prompt = "Paste audio URL: "
        elif c == "U": self._update()
        elif c == "Q": self.root.destroy()

    def _url_key(self, ev):
        if ev.keysym == "Return":
            self._download()
        elif ev.keysym == "Escape":
            self.mode = "menu"; self.input_text = ""
            self._prompt = "Pick: "
        elif ev.keysym == "BackSpace":
            self.input_text = self.input_text[:-1]
            self._prompt = self._fmt_prompt()
        elif ev.char and len(ev.char) == 1:
            self.input_text += ev.char
            self._prompt = self._fmt_prompt()
        self._redraw()

    def _fmt_prompt(self):
        p = "Paste video URL: " if self.dltype == "video" else "Paste audio URL: "
        return p + self.input_text

    def _paste(self, ev=None):
        if self.mode != "url":
            return
        try:
            self.input_text = self.root.clipboard_get().strip()
            self._prompt = self._fmt_prompt()
            self._redraw()
        except tk.TclError:
            pass

    def _download(self):
        url = self.input_text.strip()
        if not url: return
        self.mode = "busy"
        self._prompt = "Downloading..."
        self._redraw()
        threading.Thread(target=self._run_dl, args=(url,), daemon=True).start()

    def _run_dl(self, url):
        out = str(Path(self.dldir) / "%(title)s.%(ext)s")
        if self.dltype == "audio":
            cmd = [self.ytdlp, "-x", "--audio-format", "mp3", "-o", out, url]
        else:
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
        self.mode = "menu"; self.dltype = None; self._prompt = "Pick: "

    def _update(self):
        self.mode = "busy"
        self._prompt = "Updating yt-dlp via Homebrew..."
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
        self.mode = "menu"; self._prompt = "Pick: "

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    App().run()
