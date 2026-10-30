# Record the Thirduni demonstration

## Decision

Record a **3:10 product-led screen recording with your voice**. Do not read all eight presentation slides. The video is mandatory (2–4 minutes); an optional pitch-deck PDF has at most eight slides. A simple recording is enough. Music and editing are unnecessary.

Use the actual deployed/current website, not a static screenshot. The homepage generated UAV film is concept artwork, not evidence of flight. Do not use it as the majority of the competition demonstration.

## Prepare once

1. Open the website on your deployed URL, or locally while checking the recording. Test that screen capture can see browser/report switches and your microphone. Record and replay 10 seconds first.
2. Open Route 01, case P0002 (reading 3, candidate 3 Rue Saint-benoit), and Route 02, P0001 (reading 33, five views, 4.5 m, Needs review) in separate tabs. Check that these exact records appear before recording.
3. Open the real saved pipeline report/output from the repository. Do not use a fake terminal run, progress bar or fabricated fresh result. If your original Colab runtime is gone, show preserved files/report instead of repairing it.
4. Keep a neutral local review note ready: “Reading visible across views; location near junction needs follow-up.” Export notes before deleting browser data.
5. Hide passwords, private Drive folders and unrelated browser tabs. Set a readable browser zoom and record at 1080p if supported.

## Screen actions and ready narration

### 0:00–0:20 · Homepage, then enter the workspace

“An address number can be easy to read and still be difficult to place correctly. Our project, UAV Address Verification, helps inspection teams compare visible house numbers with official address records and review the evidence behind each case.”

Click **Explore the demo** promptly. Do not spend 20 seconds watching the background film.

### 0:20–0:40 · Brief architecture explanation

“Our software processes inspection imagery offline. It detects number plates, reads the numbers, combines observations across views and compares estimated positions with the address register. The website is the review workspace for those outputs, rather than the model-processing server.”

You may briefly show the architecture diagram from the optional deck, but a slide is not required.

### 0:40–1:00 · Actual saved processing evidence

“For this demonstration we used recorded Paris imagery. These are the saved source views, detections and verification outputs from that processing. The website opens those same results. This is previously processed material, not a claim of new inference during playback.”

Open an actual crop/report/output table, then return to the same recording in the website. You do not need a full sequence run. If an existing Colab environment already works, a short fresh-image batch may be added, but avoid a new setup, conversion or server deployment. Clearly identify any edited waiting time. One image alone does not validate multi-view location estimates.

### 1:00–1:55 · Real browser interaction

“Here an operator can inspect the source image and number reading, then compare the register candidate and location assessment. These checks are separate. A number matching the register does not automatically confirm the plate's position.”

Show Route 01 P0002, its source view and candidate. Then open Route 02 P0001.

“In this case the number is 33, supported by five views. The matching register point is 4.5 metres from the estimated plate position. The system keeps it marked Needs review. I can compare the supporting views and location before deciding what to follow up.”

Click two crops and show the map/selected candidate. Keep technical scores collapsed unless needed. Do not call detector confidence end-to-end accuracy or camera GPS the plate position.

### 1:55–2:25 · Review and export

“I can record a review note without changing the original assessment, then export the cases or my notes for further inspection. In this prototype notes stay in this browser; it is not yet a shared review system.”

Type the neutral note, save it, reload to demonstrate persistence and export either CSV or review JSON.

### 2:25–2:45 · Recorded playback

“Playback follows the recorded capture order so a reviewer can navigate the inspection route. It displays saved results; it does not rerun the models.”

Play briefly, pause, seek to a useful capture and switch camera side. Do not imply that markers appearing are new live detections.

### 2:45–3:10 · Close with implemented scope and next step

“The current prototype connects image processing, address comparison and evidence review. The next stage is independent street validation and a UAV acquisition interface, followed by controlled trials subject to hardware, safety and permissions. Aerial acquisition and flight control are not implemented in this demonstration.”

Stay in the app or show one closing slide. Stop recording at roughly 3:10.

## If asked why inference is not hosted in the website

“We separated batch processing from evidence review. The models run offline and the browser stays focused on inspection. This lets us demonstrate the complete review workflow without requiring model execution on each visitor's device. For future UAV use, processing hardware and throughput will be measured before choosing an edge or server deployment.”

Do **not** say a UAV inherently requires offline processing, every PC is too weak, a free server cannot run the models, or the system has proven large-scale capacity. Those statements are untested. Small weights alone do not establish end-to-end performance, and recorded detector milliseconds are not full-sequence throughput.

## Upload and submit

Upload the actual recording to unlisted YouTube or a publicly viewable equivalent. Check audio, readable text, 2–4 minute length and playback from a private/logged-out window. Put the video URL in Demo video, deployed site URL in Live demo, public code URL in GitHub. The pitch-deck PDF is separate. Submit before **31 October 2026, 23:59 Algiers**. Keep public links available during 1–7 November judging.
