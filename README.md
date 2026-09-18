# Duplex-MPE Project Page

Project homepage for **Duplex-MPE: Benchmarking Multi-Party Interaction in
Full-Duplex Dialogue**.

[Benchmark repository](https://github.com/step-out/MPEval)

The page includes the project title and author list, three benchmark figures, recorded audio
examples with synchronized waveforms and transcripts, explicit/implicit results, and BibTeX.
It is a static HTML/CSS/JavaScript site; no build step, API key or backend is required.

## Deploy on GitHub Pages

1. Open this repository's **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Select branch **main**, folder **/(root)**, then click **Save**.

After GitHub finishes deployment, the project URL is:

**https://step-out.github.io/Duplex-MPE-Page/**

The entry point is `index.html` in the repository root. `.nojekyll` tells GitHub Pages
to serve the static files directly. All local resources use relative paths, so the
project URL works without a custom domain or path configuration.

## Local preview

```bash
python scripts/serve_site.py --port 8000
```

Open http://localhost:8000. When working through a remote editor, forward remote port
8000 to your local machine first. The preview server supports byte-range requests
for seeking in audio. It binds only to localhost by default.

## Files

| Path | Purpose |
|---|---|
| `index.html` | Page sections, copy, links and citation |
| `styles.css` | Desktop and mobile styling |
| `app.js` | Audio selection, timeline interaction, results and citation copying |
| `data.js` | Authors, result values, transcripts and demo metadata |
| `assets/audio/` | 16 selected stereo MP3 excerpts |
| `assets/figures/` | Original figure PDFs and web images |
| `assets/provenance.json` | Source hashes and export conventions |
| `scripts/` | Local preview and browser verification |

Audio excerpts compare four selected systems on the same human dialogue within each
metric. Names are displayed only for examples that pass the selected metric. Failed
and ineligible examples use anonymous labels that are independent for each metric.
The aggregate result table includes all five evaluated systems. These examples are
illustrative selections, not a replacement for the complete results.

In the stereo audio, human speech is on the left and model speech is on the right.
Each track is normalized separately for listening, with recorded timing preserved.
N4 clips include both the question and the following human answer at their recorded
positions. Waveforms display audio amplitude, not the evaluation speech detector.
The N4 model transcript covers the question and answering gap as labelled on the page.
Recording identity mappings are not included in this repository.

## Update the page

- Edit prose, links and the BibTeX block in `index.html`.
- Update author and result data in `data.js` from the current manuscript and validated results.
- Replace figure assets when the paper changes.
- Keep anonymous example IDs and file names free of model identities.
- The manuscript PDF and paper download buttons are currently withheld.
  Restore a paper link only after the authors request publication.

The **Code** button links to the benchmark repository, not this website repository.
The **Dataset** section links to the benchmark's data documentation.

## Verification

The browser checks require Python, Playwright and Google Chrome at
`/usr/bin/google-chrome`:

```bash
python -m pip install playwright
python scripts/test_site.py
```

They verify all 16 audio clips, model switching and playback reset, timeline seeking,
metric-dependent name display, missing-audio recovery, addressing-condition switching, clipboard
copying, mobile layout and local asset availability.

The website code uses the repository's [MIT license](LICENSE).
