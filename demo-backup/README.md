# Demo Backup

Material used as a fallback during the demo when running `bin/demo-invoke`
live on the presenter's laptop isn't possible (e.g. no docker installed,
no SSH path to the dev machine, network problems on demo wifi).

## File: `demo-invoke.txt`

Verbatim transcript of a clean `bin/demo-invoke` run captured from the
prototype Linux machine. The output is from the published image
`seadas/find-make-matchup-harmony:latest` (digest matches what's on
DockerHub at the time of capture). Total elapsed time of the captured
run: ~12 s after the image pull cache hit.

### Narration-by-section

Use the section headers in the file as scroll-stops. Read the section
title aloud, narrate, then scroll to the next.

| Marker in transcript | What it shows | Talking point |
| --- | --- | --- |
| `==> Image:` / `==> Out dir:` | Which image and output dir the run uses | "We're pulling the same image Harmony will pull in production, public DockerHub, no auth." |
| `==> Pulling …` | Docker pull progress; ends with `Digest: sha256:…` | "This digest is the immutable identifier for the published artifact &mdash; we can verify on DockerHub it matches." |
| `==> Running Harmony invoke` | Service container starts; JSON log lines from the adapter | "Inputs picked from STAC item, parameters from the Harmony message; engine processes one granule." |
| `Processed 1 granule(s)` | Adapter confirms completion | "Eleven seconds of wall time. Engine is reusable outside Harmony &mdash; this same call path drives `run_local_matchup.py`." |
| `timing.…end` with `durationMs` | Total adapter runtime in ms | "11&ndash;12 s per granule on this hardware." |
| `==> Output data:` | The augmented SeaBASS file's listing | "Output is a new SeaBASS file, same row count as the input, with new sat columns appended." |
| `==> Output STAC catalog + item:` | The Harmony-format STAC catalog Harmony returns | "Harmony's contract output: catalog + item + asset key `data`." |
| `==> Input vs output SeaBASS /fields= diff:` | The "before vs. after" payoff | "This is the value-add. Six columns appended per row: matchup distance + time delta, plus mean/median/std/n of the requested satellite variable." |
| `Appended by matchup (6):` block | Explicit list of appended fields | "These are exactly what a validation scientist needs to compute residuals against the in-situ measurement." |

### How to present from the transcript

**Easiest path** (zero tools beyond the laptop's default editor):

1. Open `demo-invoke.txt` in TextEdit (or VS Code, or any text viewer).
2. Resize the window to take ~70&percnt; of the screen. Increase font size
   to ~20pt for projector legibility.
3. At beat 4 of the runbook, switch to that window and scroll slowly
   while reading the talking points above.
4. After the field-diff section, switch to your browser:
   <https://hub.docker.com/r/seadas/find-make-matchup-harmony>
   to show the published image is real, public, and was pushed today
   (or whenever the latest commit landed).

**Optional polish.** Pre-highlight the `Appended by matchup (6):` block
in your editor (yellow background, bold, whatever) so when you scroll to
it, the eye locks on. That's the line that makes the demo *land*.

## Refreshing the transcript

If the engine output changes (e.g. new columns appended), regenerate the
transcript by running, from the prototype dir on a docker-capable host:

```bash
bin/demo-invoke 2>&1 | tee /path/to/demo-backup/demo-invoke.txt
```

Then commit the updated file so the laptop demo session pulls the latest
text on its next `git pull`.
