---
name: audio-transcription
description: >-
  Produce a high-quality transcript AND a cleaned-up written summary of an audio
  recording using Google Gemini 3.1 Pro. Use this whenever the user wants to
  transcribe audio, get a transcript of a recording, or a writeup/summary/notes
  from a recording — interviews, podcasts, meetings, voice memos, lectures,
  phone calls — including when they just point at an audio file (.mp3, .wav,
  .m4a, .flac, .aac, .ogg) and say "transcribe this", "what's said in this",
  "write this up", or "give me notes from this". Trigger even if they don't say
  the word "transcribe" but clearly want the spoken content of an audio file
  turned into text.
---

# Audio transcription + writeup

Turn an audio recording into two deliverables:

1. **A verbatim transcript** — speaker-labeled, with `[MM:SS]` timestamps.
2. **A detailed cleaned-up writeup** — a structured, readable synthesis of the content.

Transcription uses **Gemini 3.1 Pro** via the Gemini API (high quality, good speaker
separation, handles technical vocabulary). The bundled script `scripts/transcribe.py`
handles the upload + transcription deterministically so you don't re-derive the API
flow each time.

## Prerequisites

- **Gemini API key** at `~/.config/gemini/key` — a single line, 39 chars, starting
  with `AIza` (a Google AI Studio key). If it's missing, ask the user for one and save it:
  ```bash
  mkdir -p ~/.config/gemini && printf '%s' 'AIza...' > ~/.config/gemini/key && chmod 600 ~/.config/gemini/key
  ```
  The script warns if the key looks malformed (wrong length/prefix). A common paste
  error drops the leading `A` — if you see a 38-char key starting `Iza`, that's it.

## Workflow

### 1. Locate the audio file
Confirm the path. Check the format and size:
```bash
ls -la "<audio>"; file "<audio>"
```
- **Supported natively:** `.mp3 .wav .aiff .aac .ogg .flac`.
- **Other formats** (`.m4a`, `.mp4`, `.opus`, `.webm`, video): transcode first, e.g.
  `ffmpeg -i input.m4a output.mp3`, then transcribe the result.

### 2. Run the transcription script — **with the sandbox disabled**
The upload streams the whole file over TLS. The sandbox's localhost network proxy
corrupts large uploads (`bad record mac` / a hang), so this step **must** run with
the sandbox disabled. The reading model should set `dangerouslyDisableSandbox: true`
on this Bash call (this is a legitimate, expected network operation, not a workaround):
```bash
python3 ~/claude-skills/.claude/skills/audio-transcription/scripts/transcribe.py "<audio>" --out "$TMPDIR/transcript_raw.txt"
```
The script prints the transcript to stdout and writes it to `--out`. It uploads, waits
for the file to become `ACTIVE`, transcribes, and deletes the uploaded file afterward.
If it warns about `finishReason` other than `STOP`, the audio was long enough to
truncate the output — split it into chunks (e.g. `ffmpeg` segments) and transcribe each.

### 3. Read and refine the transcript
Read the transcript. If the audio reveals real speaker names (people introduce
themselves, or the filename names someone), relabel `Speaker 1/2` with the actual names —
this makes both deliverables far more useful:
```bash
sed -e 's/Speaker 1:/Alice:/g' -e 's/Speaker 2:/Bob:/g' transcript_raw.txt > transcript_named.txt
```
Sanity-check obvious mis-hearings of proper nouns against context, but do not rewrite
the speakers' words — the transcript's value is fidelity.

### 4. Write the cleaned-up writeup
This is a synthesis task — do it yourself from the transcript; don't hand it to a fixed
prompt. The goal is something a reader who never heard the audio can read in a few
minutes and come away with the substance. Adapt structure to the content, but a strong
default:

- A short italic header line: what this is, who's speaking, the rough arc.
- **Sections by topic** (not by timestamp), with descriptive headings following the
  conversation's natural movement.
- Preserve concrete substance: specific numbers, names, claims, examples, disagreements.
  Turn rambling speech into clean prose, but don't flatten it into vague generalities —
  the details are the point.
- Use tables for comparisons or structured data, and bold for key terms.
- End with a **Key takeaways** list (the few things worth remembering).

Keep it faithful: capture what was actually said, attribute claims to whoever made them,
and don't invent facts or smooth over uncertainty the speakers expressed.

### 5. Save both deliverables to ~/Downloads
Default output location is the user's Downloads folder. Use the recording's name as the
stem. Writing to `~/Downloads` needs the sandbox disabled:
```bash
cp "$TMPDIR/transcript_named.txt" ~/Downloads/"<name> - transcript.txt"
# write the writeup markdown to ~/Downloads/"<name> - writeup.md"
```
Then give the user a short summary: where the files are, who the speakers are, and a
one-line description of the content. Flag anything notable (truncation, audio quality
issues, uncertain speaker identification).

## Gotchas

- **Sandbox off for upload and for `~/Downloads`/`~/.config` writes.** Transcription
  request itself works inside the sandbox; only the big upload and out-of-sandbox file
  writes need it disabled.
- **Files over 20 MB** must use the Files API — the script always does, so no special
  handling needed.
- **Very long audio** (roughly >45 min) can exceed Gemini's 65k output-token limit and
  truncate. The script warns; chunk and re-run if so.
- **Key format:** 39 chars, `AIza` prefix. An invalid key surfaces as an
  "API key not valid" error from the upload-start call.
