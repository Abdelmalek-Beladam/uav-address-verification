# Data formats

All CSV files may use comma or semicolon separators and UTF-8 with or without BOM. Outputs are written
as UTF-8 with BOM so that Excel opens them correctly.

## Inputs

### Photo metadata (`--metadata`)

CSV, JSON or GeoJSON exported with the dataset. One row per 360 photo.

| Column | Required | Meaning |
|---|---|---|
| sequence_number | yes | Order of the photo along the route. |
| picture_id | yes | Panoramax picture id. |
| latitude, longitude | yes | Camera position (WGS84). |
| travel_bearing | yes | Direction of travel, degrees clockwise from north. |
| distance_to_street_m | no | Used to skip photos far from the street. |
| datetime, sequence_id, source_url, panorama_azimuth, original_360_file | no | Kept for reference. |
| `<view>_file` | yes per view | Path of the crop, for view = forward, left, right. |
| `<view>_global_direction` | yes per view | Direction the centre of the crop looks at. |
| `<view>_horizontal_fov` | yes per view | Horizontal field of view in degrees. |
| `<view>_pitch` | no | Camera pitch in degrees (negative = looking down). |
| `<view>_relative_yaw` | no | Kept for reference. |

### Address register (`--addresses`)

The Paris file `adresse_paris.csv` as downloaded (semicolon separated). Columns used: `Geometry X Y`
("lat, lon"), `N_VOIE` (number), `C_SUF1` (suffix b/t/q/c), `C_SUF2`/`C_SUF3` (letters), `L_ADR`
(full address), `L_NVOIE`, `N_SQ_VO` (street id), `A_NVOIE` (street angle), `B_ANGLE` (corner flag),
`N_SQ_AD`. Only addresses within 40 m of the route are loaded.

### Plate detections (`--detections`)

One row per plate box, from the annotator or from the model.

| Column | Required | Meaning |
|---|---|---|
| image | yes | Crop file name (for example `000012_left.jpg`), matched with the metadata. |
| view | no | left, right or forward. Taken from the metadata when missing. |
| x_min, y_min, x_max, y_max | yes | Box in pixels. |
| image_width, image_height | recommended | Crop size in pixels. If missing, read from the image with Pillow (needs `--images-root`). |
| text | yes | Number as written: "12", "12 bis", "17 A". "?" or empty = unreadable. |
| det_conf, ocr_conf | no | Model confidences between 0 and 1. Manual rows count as 1. |
| source | no | manual or model name. |

### Reviewed crops (`--reviewed`, optional)

One column `image` (and optionally `view`): the crops that a person checked completely, including the
ones with no plate. Crops that have a detection are always counted as checked. Without this file,
every crop in the metadata is assumed to have been checked, so leave it out only when the whole
sequence was labelled.

## Outputs

| File | Content |
|---|---|
| report.html | Map and tables for everyone. Works offline for tables; the map needs internet. |
| addresses.csv | One row per official address in scope: status, explanation, confidence, photos in view, plates linked. |
| plates.csv | One row per plate: reading, votes, position and how it was found, matched address, status, explanation. |
| detections.csv | Every input detection with its sight-line direction, plate id, or the reason it was ignored. |
| photos.csv | Every photo: used or skipped with the reason, corrected position. |
| expected_views.csv | For each crop, the addresses that should be clearly visible in it. |
| results.geojson | Photos, addresses, plates, sight lines and links, for QGIS or the web app. |
| summary.json | Counts by status, GPS correction, settings used and warnings. |

Status codes in the CSV files: CORRECT, NOT_FOUND, SUFFIX_MISMATCH, WRONG_SIDE, OUT_OF_PLACE,
UNKNOWN_NUMBER, NO_ADDRESS_NEARBY, UNREADABLE, UNCERTAIN, INSUFFICIENT_VIEWS, NOT_COVERED, IN_VIEW
(inspect mode). The `status_label` column gives the readable name.
