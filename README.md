# Lazy Downloader

A retro green-on-black terminal-style downloader for macOS. Paste a URL, hit Enter, done. No Python in the Dock — ships as a standalone `.app`.

## What it does

Downloads video and audio from YouTube, Twitter/X, Substack, TikTok, and hundreds of other sites — anything [yt-dlp](https://github.com/yt-dlp/yt-dlp) supports.

## Features

- **Video download** — best available mp4 + m4a audio, merged to mp4
- **Video clip download** — grab just a segment: give a start and end time and only that part is saved
- **Audio download** — extracted and converted to mp3
- **Audio clip download** — just a segment of the audio, saved as mp3
- **Update yt-dlp** — refreshes the downloader from the menu (YouTube changes things often)
- **Keyboard-driven** — type `1` or `2`, paste a URL (⌘V or right-click), Enter to download
- **Green phosphor on black** — matches the classic terminal aesthetic

## Usage

Launch the app, then:

```
 [1]  Video download          (yt-dlp)
 [2]  Audio download          (yt-dlp)
 [3]  Video CLIP download     (start/end)
 [4]  Audio CLIP download     (start/end)
 [U]  Update yt-dlp
 [Q]  Quit
```

Press `1` or `2`, paste a URL, press Enter. Files land on your Desktop. `Esc` cancels back to the menu.

### Cutting a clip

Press `3` for a video clip or `4` for an audio clip, paste a URL, press Enter — then it
asks for the two times:

```
Paste video URL to clip: https://youtu.be/xxxxxxxxxxx      ([3])
Paste audio URL to clip: https://youtu.be/xxxxxxxxxxx      ([4])
Clip START (mm:ss / h:mm:ss, ENTER = 0:00): 1:30
Clip END (mm:ss / h:mm:ss, ENTER = to end): 2:45
```

Times can be written three ways:

| You type | Means |
|---|---|
| `90` | 90 seconds |
| `1:30` | 1 min 30 sec |
| `0:01:30.5` | 1 min 30.5 sec |

Press Enter on the start prompt to begin at `0:00`, or on the end prompt to run to the
end of the video. Bad input (e.g. `1:99` — minutes and seconds fields must be 0-59) is
caught before anything downloads, and the text stays on screen for you to fix.

The clip is saved next to the full downloads, with the range in the filename:

```
Video Title [clip 0-01-30_0-02-45].mp4
Video Title [clip 0-01-30_0-02-45].mp3     ([4] audio clips)
```

Cuts are frame-accurate (`--force-keyframes-at-cuts`), which means ffmpeg re-encodes the
segment — a clip takes a bit longer than the same amount of full-video download. Audio
clips use the same flag: without it the cut snaps to the nearest video keyframe and you
get extra audio (measured 8 seconds of audio for a 5-second request).

## Dependencies

The app bundles its own Python + tkinter, but still needs two command-line tools installed:

```bash
brew install yt-dlp ffmpeg
```

`ffmpeg` is needed by **all four** options: clips use it to cut, mp3 uses it to convert,
and the full-video option uses it to merge the separate video and audio streams into one
mp4.

### Why the app has to tell yt-dlp where ffmpeg is

macOS gives an app launched from the Dock or Finder a minimal `PATH`
(`/usr/bin:/bin:/usr/sbin:/sbin`), so it cannot see anything Homebrew installed. yt-dlp
looks for ffmpeg on `PATH`, and without finding it:

- clip downloads abort with *"You have requested downloading the video partially, but
  ffmpeg is not installed"*
- mp3 conversion fails
- full video downloads silently leave **two** unmerged files (`…​.f140.m4a` and
  `…​.f395.mp4`) instead of one mp4

So the app locates yt-dlp, ffmpeg and brew by absolute path rather than relying on `PATH`,
passes `--ffmpeg-location` to yt-dlp, and gives subprocesses a `PATH` that includes
`/opt/homebrew/bin`. Menu option `[U]` calls brew by full path for the same reason.

If a tool is missing the menu says so at startup, and downloads refuse with
`FAILED: missing ffmpeg — run: brew install ffmpeg` instead of half-succeeding.

## Building the standalone .app

```bash
brew install pyinstaller python-tk@3.14
./build.sh
```

The `.app` lands in `dist/` — drag it to `/Applications` and your Dock.

### Why `python-tk`?

macOS's system Python (`/usr/bin/python3`) ships **Tk 8.5** — a 2007-era GUI toolkit that can draw window frames but *not* text on modern macOS. The symptom is a blank window with only a title bar. Installing `python-tk@3.14` gives the Homebrew Python a modern **Tk 9.0**. The script's shebang points at `/opt/homebrew/bin/python3` for this reason.

## Icon

- `make_icon.py` — programmatically generates the *download-arrow* icon (pure Python, no image libraries needed)
- `assets/monkey-icon.png` — the *monkey-at-keyboard* icon (AI-generated, 1024×1024). This is the icon currently used by the shipped app. Convert it to `.icns` and pass `--icon` to the build script to use it.

## License

MIT
