#!/usr/bin/env python3
"""Upload an audio file to the Gemini Files API and transcribe it with Gemini 2.5 Pro.

Usage:
    transcribe.py <audio-file> [--out <transcript.txt>] [--prompt <prompt.txt>]

- Reads the API key from ~/.config/gemini/key (a single-line AI Studio key, "AIza...").
- Uploads via the resumable Files API (required for files over the 20 MB inline limit;
  used unconditionally here so the same path works for any size).
- Transcribes with gemini-2.5-pro and prints the transcript to stdout.
- Writes to --out as well if given. Deletes the uploaded file afterward.

IMPORTANT: run this with the sandbox DISABLED. The sandbox's localhost network proxy
corrupts large TLS uploads (you'll see "bad record mac" / a hang). Plain stdlib only.
"""
import sys
import os
import json
import time
import urllib.request
import urllib.error

MODEL = "gemini-2.5-pro"
BASE = "https://generativelanguage.googleapis.com"
KEY_PATH = os.path.expanduser("~/.config/gemini/key")

DEFAULT_PROMPT = """Transcribe this audio in full, verbatim. Requirements:
- Identify distinct speakers and label each turn (use real names if they are stated \
in the audio; otherwise Speaker 1, Speaker 2, etc.).
- Insert an approximate timestamp [MM:SS] at the start of each speaker turn and at \
major topic shifts.
- Transcribe the actual words spoken. You may drop excessive filler (um, uh, repeated \
false starts) for readability, but do NOT paraphrase or summarize — keep it a faithful \
word-for-word transcript.
- Spell out proper nouns, company names, and technical terms as accurately as you can.
- Output plain text only, no commentary."""

# MIME types Gemini accepts natively. For anything else (m4a, mp4, opus, webm, ...),
# transcode first, e.g.  ffmpeg -i input.m4a output.mp3
MIME = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".flac": "audio/flac",
}


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def get_key():
    try:
        k = open(KEY_PATH).read().strip()
    except FileNotFoundError:
        die(f"No Gemini API key at {KEY_PATH}.\n"
            "Create it with your Google AI Studio key:\n"
            "  mkdir -p ~/.config/gemini && printf '%s' 'AIza...' > ~/.config/gemini/key && chmod 600 ~/.config/gemini/key")
    if not k:
        die(f"Key file {KEY_PATH} is empty.")
    if not k.startswith("AIza") or len(k) != 39:
        print(f"WARNING: key looks malformed (len={len(k)}, prefix={k[:4]!r}). "
              "Valid AI Studio keys are 39 chars starting with 'AIza'.", file=sys.stderr)
    return k


def http(url, data=None, headers=None, method=None):
    r = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        resp = urllib.request.urlopen(r)
        return resp.status, {k.lower(): v for k, v in resp.getheaders()}, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        die("Usage: transcribe.py <audio-file> [--out <file>] [--prompt <file>]")
    audio = args[0]
    out = None
    prompt = DEFAULT_PROMPT
    i = 1
    while i < len(args):
        if args[i] == "--out":
            out = args[i + 1]; i += 2
        elif args[i] == "--prompt":
            prompt = open(args[i + 1]).read(); i += 2
        else:
            die(f"Unknown argument: {args[i]}")

    if not os.path.isfile(audio):
        die(f"File not found: {audio}")
    ext = os.path.splitext(audio)[1].lower()
    mime = MIME.get(ext)
    if not mime:
        die(f"Unsupported audio format '{ext}'. Gemini accepts: {', '.join(sorted(MIME))}.\n"
            f"Transcode first, e.g.:  ffmpeg -i {audio!r} output.mp3")

    key = get_key()
    nbytes = os.path.getsize(audio)
    display = os.path.splitext(os.path.basename(audio))[0]
    print(f"Uploading {audio!r} ({nbytes/1e6:.1f} MB, {mime})...", file=sys.stderr)

    # 1. Start resumable upload session.
    status, hdrs, body = http(
        f"{BASE}/upload/v1beta/files?key={key}",
        data=json.dumps({"file": {"display_name": display}}).encode(),
        headers={
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(nbytes),
            "X-Goog-Upload-Header-Content-Type": mime,
            "Content-Type": "application/json",
        },
    )
    if status != 200:
        die(f"Upload start failed ({status}): {body.decode(errors='replace')[:600]}")
    upload_url = hdrs.get("x-goog-upload-url")
    if not upload_url:
        die("No upload URL returned (check that the API key is valid).")

    # 2. Upload the bytes and finalize in one shot.
    with open(audio, "rb") as f:
        blob = f.read()
    status, hdrs, body = http(
        upload_url,
        data=blob,
        headers={
            "Content-Length": str(nbytes),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        },
    )
    if status != 200:
        die(f"Upload failed ({status}): {body.decode(errors='replace')[:600]}")
    finfo = json.loads(body)["file"]
    fname, furi, state = finfo["name"], finfo["uri"], finfo.get("state")

    # 3. Wait until the file finishes server-side processing.
    waited = 0
    while state == "PROCESSING" and waited < 180:
        time.sleep(3); waited += 3
        s, _, b = http(f"{BASE}/v1beta/{fname}?key={key}")
        if s == 200:
            state = json.loads(b).get("state")
    if state != "ACTIVE":
        die(f"Uploaded file never became ACTIVE (state={state}).")

    # 4. Transcribe.
    print("Transcribing with gemini-2.5-pro...", file=sys.stderr)
    reqbody = {
        "contents": [{"role": "user", "parts": [
            {"file_data": {"mime_type": mime, "file_uri": furi}},
            {"text": prompt},
        ]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 65000},
    }
    status, _, body = http(
        f"{BASE}/v1beta/models/{MODEL}:generateContent?key={key}",
        data=json.dumps(reqbody).encode(),
        headers={"Content-Type": "application/json"},
    )
    # Clean up the uploaded file regardless of outcome (it also auto-expires in 48h).
    http(f"{BASE}/v1beta/{fname}?key={key}", method="DELETE")

    d = json.loads(body)
    if status != 200 or "candidates" not in d:
        die(f"Transcription failed ({status}): {json.dumps(d)[:600]}")
    cand = d["candidates"][0]
    reason = cand.get("finishReason")
    if reason not in (None, "STOP"):
        print(f"WARNING: finishReason={reason} — transcript may be truncated. "
              "For very long audio, consider splitting it into chunks.", file=sys.stderr)
    text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    usage = d.get("usageMetadata", {})
    print(f"Done: ~{len(text.split())} words, {usage.get('totalTokenCount','?')} tokens.",
          file=sys.stderr)

    if out:
        with open(out, "w") as f:
            f.write(text)
        print(f"Wrote transcript to {out}", file=sys.stderr)
    print(text)


if __name__ == "__main__":
    main()
