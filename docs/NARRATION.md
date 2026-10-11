# BaadhDrishti — narration script (read aloud, ~3:00)

Rules: every number below is script/API output from this repo (verified 2026-10-11) — do not add others.
Pace: calm, ~140 words per minute. Total ≈ 410 words → ≈ 2:55. Pause ~1 s at each `//`.
Record in one take if you can (re-reading a scene is fine — leave a 2 s gap before the retake; I will cut it).

Pronunciation: Budameru = *boo-DAH-meh-roo* · Vijayawada = *vi-jay-uh-WAH-da* · Tadepalle = *TAH-deh-pul-lay* ·
Vissannapeta = *vis-SUN-nuh-pay-ta* · Paidurupadu = *pie-DOO-roo-pah-doo* · BaadhDrishti = *BAADH-drish-tee*

---

## Scene 1 — Hook (0:00–0:35) · dark title interface, question types out, answer streams, count-up card

In September 2024, the Budameru flood swept through the villages around Vijayawada. //
Satellite flood maps came quickly. They showed where the water was. //
But a control room has a sharper question: //
which villages have lost every mapped road to a hospital — and where should field teams verify first? //
In this replay, the answer is seven habitations. //
About nine thousand three hundred people, by population estimate. //
This is BaadhDrishti.

## Scene 2 — Radar (0:35–1:10) · live app: slider 20 Aug → 1 Sep, water mask, urban core

BaadhDrishti starts with Sentinel-1 radar from AWS Open Data. Radar sees through monsoon cloud. //
We calibrate the image from the twentieth of August and the one from the first of September, //
and mark where the ground suddenly turned as dark as open water. //
Permanent rivers and steep slopes are masked out. //
And the dense city core is excluded and clearly labelled — radar bounces off buildings, so city flooding is ambiguous. //
The official NRSC flood map leaves it out too.

## Scene 3 — Roads and the queue (1:10–1:50) · red roads, queue panel, zoom to Tadepalle

A flood map alone is not the answer. //
We turn more than twenty-six thousand OpenStreetMap road segments into a graph. //
Any road next to candidate water is treated as blocked — except bridges. Bridges are never closed automatically; they are flagged for a field check. //
Then, for every habitation, we ask one question: is any mapped road path left to a hospital? //
Seven peri-urban habitations have none. //
Tadepalle tops the queue — about two thousand four hundred people — cut off on the Vijayawada–Vissannapeta Road.

## Scene 4 — The officer acts (1:50–2:30) · clear road → hub → bridge

Disaster response needs a human in the loop. //
A field report says that stretch of road is passable. The officer marks it cleared — //
and AWS Lambda recomputes reachability in well under a second. Five habitations get a path back. //
For Paidurupadu, the officer nominates a dry staging point — and it is connected too. //
But if the bridge on that same road is reported down, the same five are cut off again. //
That is exactly why bridges are flagged, not guessed. //
The queue goes to field teams on WhatsApp, or as a spreadsheet.

## Scene 5 — Architecture (2:30–2:50) · animated architecture diagram

Under the hood: Sentinel-1 from AWS Open Data, processed once offline into Amazon S3. //
Amazon API Gateway and AWS Lambda run the road engine on every officer edit, //
officer decisions live in Amazon DynamoDB, //
and the whole app is a single page on Amazon S3 — deployed with AWS SAM.

## Scene 6 — Close (2:50–3:00) · disclaimer, live URL, repo

BaadhDrishti is not a rescue order and not a forecast. //
It is an honest, verification-first queue — so officers know where to look first.

---

## Recording tips
- Phone voice memo or laptop mic is fine. Quiet room, phone ~20 cm from mouth, no fan.
- Export as `.m4a`, `.wav` or `.mp3`. Send the raw file; I will trim, level and time the scenes to your words.
- If you stumble, pause 2 s and repeat the whole sentence.
