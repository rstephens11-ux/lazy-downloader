# Lazy Downloader

A retro green-on-black terminal-style downloader for macOS. Paste a URL, hit Enter, done. No Python in the Dock — ships as a standalone `.app`.

## What it does

Downloads video and audio from YouTube, Twitter/X, Substack, TikTok, and hundreds of other sites — anything [yt-dlp](https://github.com/yt-dlp/yt-dlp) supports.

## Features

- **Video download** — best available mp4 + m4a audio, merged to mp4
- **Audio download** — extracted and converted to mp3
- **Update yt-dlp** — refreshes the downloader from the menu (YouTube changes things often)
- **Keyboard-driven** — type `1` or `2`, paste a URL (⌘V or right-click), Enter to download
- **Green phosphor on black** — matches the classic terminal aesthetic

## Usage

Launch the app, then:

```
 [1]  Video download          (yt-dlp)
 [2]  Audio download          (yt-dlp)
 [U]  Update yt-dlp
 [Q]  Quit
```

Press `1` or `2`, paste a URL, press Enter. Files land on your Desktop. `Esc` cancels back to the menu.

## Dependencies

The app bundles its own Python + tkinter, but still needs two command-line tools installed:

```bash
brew install yt-dlp ffmpeg
```

`ffmpeg` is only needed for the audio-only (mp3) option.

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
- The *monkey-at-keyboard* icon is AI-generated (no script; the raw PNG is not committed)

## License

MIT
