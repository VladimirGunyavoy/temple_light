# sim/ — standalone CSV/JSON export (no Ursina required)

`wall_example.py` is a separate, independent tool from `../main.py`: it
builds a simple flat test wall of columns lit by one spotlight, using the
same `Luminaire`/`Segment`/`Column` classes from `../src/`, and writes the
result to CSV/JSON without needing `ursina` installed. **It is still on
the older flat-wall scenario** — it has not been updated to the ring/
spiral structure or occlusion that `main.py` now uses.

```
python wall_example.py
```

writes `wall_example_output.csv` (one row per segment/ray) and
`wall_example_viz.json` (heatmap grid + full per-ray detail) into this
folder — both gitignored, regenerated on every run.

`spiral_line_intersection.ipynb` is where the ray/spiral-curve
intersection method (used by `src/spiral.py`'s occlusion check) was
validated *before* being ported into production code: it checks the
analytic spiral curve against the discrete column positions, checks
intersection-finding correctness (including the on-segment vs.
on-infinite-line distinction), and visualizes both. Needs `numpy` +
`matplotlib` and a Jupyter kernel with those installed.
