# BaadhDrishti — 3-minute demo video

Rules: every number on screen or in the voiceover comes from the live UI/API or this repo's script output.
APSDMA / cusecs figures are **TO VERIFY** — they are left out below; add them only with a citation on screen.

## Before recording (checklist)
- [ ] `AWS_PROFILE=baadh scripts/reset_demo_state.sh` → both tables `0 items`.
- [ ] Open the FrontendUrl in a fresh browser window (1440×900 or 1920×1080), reload once to warm the Lambda.
- [ ] Stats bar reads: 40 in scope · 7 no mapped road path · 9,314 population proxy · compute ms (note the value: ____ ms).
- [ ] Demo sequence (live-tested 2026-10-11 against the API, then reset): start 7 cut off →
      (1) Tadepalle "Clear blocking roads" → 2 left (Paidurupadu, Elaprolu) →
      (2) "+ Add staging hub" at **16.6059, 80.5804** (dry point in our mask, 644 m NNE of the Paidurupadu village point; name it
      "Paidurupadu dry staging point", kind RELIEF_CAMP) → 1 left (Elaprolu) →
      (3) optional: orange bridge on Vijayawada–Vissannapeta Road at **16.6291, 80.6172** → "Mark blocked" → 6 cut off
      (the 5 restored in step 1 lose their path again).
      Zoom to the hub point first: every tested click within 150 m of 16.6059, 80.5804 restored Paidurupadu (25/25).
- [ ] Have `docs/architecture.png` open in another tab.
- [ ] Between takes and after recording: run the reset script again (each take must start from 7 cut off).

## Shot list

| Time | Screen | Voiceover |
|---|---|---|
| 0:00–0:25 | Title card → NRSC/APSAC 6-Sep-2024 map PDF (cite on screen) | "In early September 2024 the Budameru flood cut villages around Vijayawada off from care. Flood maps show where the water is. A control room also needs to know: which villages have no mapped road left to a hospital, and where should field teams verify first?" |
| 0:25–1:05 | BaadhDrishti opens. Drag the slider 20 Aug → 1 Sep, toggle the blue water mask, hover the amber urban core | "BaadhDrishti uses Sentinel-1 radar from AWS Open Data — it sees through cloud. We calibrate the 20 August and 1 September images, detect where the radar return dropped like open water, and mask permanent water and slopes. The dense urban core is excluded and labelled, because radar double-bounce makes city flooding ambiguous — the official NRSC map excludes it too." |
| 1:05–1:45 | Red road segments; queue on the right; click row #1 Tadepalle → Zoom | "The difference is the road network. We turn OpenStreetMap roads into a graph, mark segments next to candidate water as suspected blocked — bridges are never auto-closed, they are flagged for checking — and ask, for every habitation, is any mapped road path left to a hospital? Seven peri-urban habitations have none. Tadepalle, population estimate 2,404, tops the verification queue; its route is blocked on the Vijayawada–Vissannapeta Road." |
| 1:45–2:25 | On Tadepalle click "Clear blocking roads" → dialog (officer name, note "tractor passable per police outpost") → toast "Restored (5): Tadepalle, Vemavaram, Jakkampudi, Kotturu, Shabada"; then "+ Add staging hub", click 16.6059, 80.5804 → toast "Restored (1): Paidurupadu"; optionally click the orange bridge at 16.6291, 80.6172 → "Mark blocked" → toast "Newly cut off (5)…" | "Disaster response is human-in-the-loop. A field report says that stretch of the Vijayawada–Vissannapeta Road is passable — the officer marks it cleared, and AWS Lambda recomputes reachability in the time shown up here: five habitations get a path back. For Paidurupadu the officer nominates a dry staging point, and it gets a destination too. And if the field team reports the bridge on that same road is down, the same five are cut off again — that is why bridges are flagged for checking, never auto-closed. The queue can be shared to WhatsApp or downloaded as CSV for field teams." |
| 2:25–3:00 | `docs/architecture.png`, then back to the app footer with the disclaimer | "Under the hood: Sentinel-1 from AWS Open Data, a one-time offline pipeline into Amazon S3, an API Gateway and Lambda engine, officer edits in DynamoDB, and a single Leaflet page on AWS S3 static website, deployed with AWS SAM. BaadhDrishti is not a rescue order or a forecast — it is an uncertainty-aware verification queue that helps officers decide where to look first." |
