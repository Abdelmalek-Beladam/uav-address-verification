# Architecture

```text
Recorded images + camera metadata
            |
Offline Python / compatible Colab environment
  detector -> crop recognition -> cross-view grouping
  -> plate position estimates -> register comparison
            |
Saved CSV/JSON, source views and plate crops
            |
Static browser review application
  filters / source inspection / map / local notes / exports / playback
```

A future UAV acquisition adapter would provide new imagery and appropriate pose/calibration metadata. It is not a current flight system. Aerial imagery cannot be assumed equivalent to the current street views without validation.

## Browser responsibilities

`product-config.js`: display labels only; saved IDs remain stable.
`information.js`: project, privacy, terms, responsible-use and source notices.
`app.js`: cache saved data, route views, render escaped evidence, manage browser-local notes, project map coordinates, export filtered results and replay capture order. No model invocation, upload endpoint or inference progress simulation exists.
`app.css` / `redesign.css`: inherited workspace/base styling. `release.css`: scoped product landing and information-page refinements. Their load order is explicit in index.html. A future CSS consolidation should retain browser regression coverage rather than remove selectors blindly.

Route changes stop playback, pause media and disconnect map observers. A route generation counter prevents obsolete fetches from overwriting newer navigation. Existing local-note keys remain unchanged. CSV cells neutralize spreadsheet formula prefixes.

## Processing boundaries

`tools/run_street.py` runs detection/OCR and delegates verification. `src/plateverif/` contains the CPU matching/reporting rules. `tools/build_dashboard_data.py` produces viewer JSON. UI changes should not trigger model runs. `tools/reproduce_saved_release.py` starts from archived raw detection rows and replays documented safety abstentions before verification.

## Evidence semantics

Camera GPS is not the plate location. A same-number candidate does not alone verify placement. Combined scores are evidence indicators, not calibrated probabilities. Junctions, unclear readings and insufficient view geometry remain review cases. Browser notes are an operator layer and do not overwrite pipeline assessments.
