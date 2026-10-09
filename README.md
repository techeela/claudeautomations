# LinkedIn card renderer

Stat cards for Deepak Joshi's daily LinkedIn posts.

- `specs/*.json`: card content, one file per post, named `YYYY-MM-DD-topic.json`
- `render.py`: draws a 1080×1350 PNG from a spec
- `.github/workflows/render-cards.yml`: on every push to `specs/`, renders new or changed specs into `cards/` and commits them
- `cards/*.png`: finished images, public at `https://raw.githubusercontent.com/techeela/claudeautomations/main/cards/<name>.png`

The daily scheduled task pushes a spec, waits for the card to appear, then attaches it to a Metricool LinkedIn draft. Nothing publishes without manual approval.
