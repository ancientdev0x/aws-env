# BaadhDrishti — SAR flood candidates, cut-off reachability and exposed-population triage

Research date: 9 October 2026. Scope: a technically honest, buildable flood-response prototype for the Bharat Builds Tour Heat & Water track. Case study: the 31 August–September 2024 Budameru / Krishna flooding around Vijayawada, Andhra Pradesh.

## Executive decision

Build BaadhDrishti only as a **post-acquisition triage and verification tool**:

1. identify satellite-derived *candidate* new open-water / inundation areas;
2. mark road edges that intersect a buffered candidate-water area as **suspected disrupted**, not “closed”; and
3. recompute which named settlement/habitation nodes lose every viable road path to a nominated staging point or facility.

The output is a ranked field-verification queue: “possible cut-off settlement + the first suspected blocking edge + source/date/confidence.” It is not a flood forecast, water-depth product, road-condition feed, navigation service, population-at-risk count, rescue dispatch engine, or official warning.

This narrow claim is both meaningful and defensible. In the 2024 Andhra Pradesh flood impact report, APSDMA describes lack of approach-road access, water over roads, road/culvert washouts and villages made inaccessible during floods. The same report says the Budameru rivulet rose to 35,000 cusecs, nearly five times its stated 7,500-cusec carrying capacity; it identifies inundation along Elaprolu, Rayanapadu, Gollapudi, Jakkampudi Colony, Singh Nagar, Gunadala and Ramavarappadu after the Velagaleru regulator received more than 30,000 cusecs on 1 September [1]. This is a credible scenario for prioritising checks, not for inferring a specific road closure from radar alone.

## Why Vijayawada 2024 is a valid case study

### Event facts, separated from product estimates

| Fact | Evidence and product implication |
|---|---|
| Intense rainfall/runoff and concurrent Krishna flooding overwhelmed the system. | APSDMA documents Budameru at 35,000 cusecs and notes the diversion channel capacity; the report describes the low-lying locations inundated downstream of Velagaleru [1]. |
| Impact was geographically broad. | APSDMA reports 905 villages/wards in 227 mandals and 27 towns affected, with 12.87 lakh people affected statewide; these are event-wide government impact figures, **not** a BaadhDrishti output [1]. |
| Road access was a material operational issue. | APSDMA explicitly records approach-road access problems, water/mud over roads, washed-out roads/culverts, and damage to 4,388.44 km of R&B roads plus 806 PR roads / 2,187.57 km [1]. Again, these are damage/impact assessments, not automatically observable from one SAR scene. |
| Independent official EO evidence exists. | NRSC published a rapid map for 5 September 2024 using a Sentinel-1A pre-event scene (20 August) and a TanDEM-X post-event scene. It labels itself preliminary, states no ground verification, and expressly says urban-area analysis is not part of that map [2]. NRSC/APSpace also published a 11 September product naming the Gollapudi–Jakkampudi–Ambapuram, Elaprolu–Kavuluru–Rayanapadu and Nunna–Vijayawada–Ramavarappadu surroundings [3]. |

The important product lesson is not “we can improve on NRSC.” It is: officially issued rapid products demonstrate that the event and broad inundation signal were real, while their own caveats establish why BaadhDrishti must surface uncertainty and route its findings to human verification.

## User and exact decision

Primary user: an NTR district / Vijayawada disaster-control analyst, or a relief organisation GIS analyst.

Decision supported: **Which settlement–road access pairs should a field/phone/boat verification team check first after a new satellite acquisition?**

A triage card contains:

- settlement or habitation name/identifier;
- baseline route to a selected staging point, relief camp, PHC, or depot;
- a binary network result: `baseline-connected` / `no remaining modeled route after suspected-edge removal`;
- suspected disrupted edge(s), their distance/overlap to water candidate, and road-source timestamp;
- acquisition time, orbit/pass, preprocessing/version and confidence class;
- resident-population proxy inside a clearly labelled buffer/catchment; and
- “verify by ground report before directing responders” status.

The analyst selects the staging point and can accept/reject a suspected edge based on official/field evidence. Recalculation then produces the next queue. This makes the consequential decision explicit and keeps the human in control.

## What the system would actually calculate

### 1. Flood-candidate surface

Preferred MVP input is a same-geometry Sentinel-1 GRD pair: one pre-event baseline and one crisis/post-event acquisition, filtered to the same relative orbit, pass, instrument mode and available polarisation. Google’s Sentinel-1 change-detection guidance says time-series images must fully overlap and use the same orbit/pass/relative orbit for an interpretable sequence [4]. Its Earth Engine Sentinel-1 GRD collection is already orbit-file corrected, noise removed, radiometrically calibrated and terrain corrected; values are sigma-nought in dB [5].

For each pixel or 30–50 m aggregation cell:

```
water_candidate = significant negative change in VV and/or VH
                  AND not permanent water
                  AND slope / HAND / layover-shadow constraints allow it
                  AND spatial patch rule is met
```

A simple ratio/threshold is acceptable only as a preliminary screen. A stronger MVP uses a pre-event seasonal median plus a crisis image, flags negative dual-polarisation change, and stores a confidence tier. Google’s published example demonstrates that negative changes in both VV and VH corresponded to widespread flood water, but also warns that built-up Beira gave a less convincing signal because of double-bounce scattering [4].

A practical tiering scheme:

| Tier | Rule | UI label |
|---|---|---|
| A — higher confidence open-water candidate | large contiguous negative VV+VH change, not permanent water, no terrain/layover mask | “Likely new open water — verify road crossing” |
| B — plausible | one-polarisation change or adjacency to Tier A | “Possible inundation — verify” |
| C — unsuitable for automated road inference | dense built-up, flooded vegetation/wetland, layover/shadow, missing comparable baseline, or noisy small patch | “SAR ambiguous — do not infer road status” |

Do not report hectares without reporting the pixel scale, mask exclusions and date. Do not call the result “flood extent” without the qualifier `satellite-derived candidate`.

### 2. Road-edge suspicion, rather than road closure

Road data is converted to graph edges. A road edge is `suspected disrupted` when it intersects the candidate-water polygon after a parameterised lateral buffer, or when a candidate intersects a bridge/culvert approach. The buffer is a sensitivity parameter to be displayed and tested; it is not a physical water-depth measurement. Candidate intersection does not prove road impassability: elevated roads, bridges, culverts, embankments, water underneath a structure, and positional/raster error all break that inference.

For each edge retain:

- source (`OpenStreetMap` / PMGSY GeoSadak / local authoritative layer), source date and tags;
- geometry version and topology-cleaning version;
- candidate class and overlap/buffer metrics;
- optional human report state: `unverified`, `passable`, `restricted`, `closed`, `cleared`, with time and reporter role.

The public PMGSY Rural Connectivity Dataset is unusually useful for a village-access MVP: the Government of India released 2.5 million+ km of rural roads, 1 million+ habitation records and 800,000+ facility points under the Government Open Data License, explicitly noting potential use in quick disaster response [6]. It is a **baseline inventory**, not a live road-closure feed. In Vijayawada’s urban core, OSM may be denser; neither OSM nor PMGSY can certify current passability.

### 3. Cut-off calculation

Let baseline road graph be `G=(V,E)`, chosen staging node be `s`, and settlement/access node be `v`. Form `E' = E − E_suspected`. A settlement is a **modelled possible cut-off** iff `v` was connected to `s` in `G` but has no path to `s` in `G'`.

```
for each settlement v:
    baseline = has_path(G, v, s)
    remaining = has_path(G without suspected_edges, v, s)
    if baseline and not remaining:
        flag v as possible_cut_off
```

Rank no-route settlements by a transparent, non-claiming score, for example:

```
priority = 0.45 * normalised population_proxy
         + 0.25 * road-evidence confidence
         + 0.20 * baseline detour / network criticality
         + 0.10 * facility-access penalty
```

The weights are editable and are not a validated life-safety model. The UI must distinguish “no remaining route in our incomplete baseline graph” from a verified isolation. Never use a straight-line distance as access proof.

### 4. Population proxy

Intersect the uncertainty-labelled candidate-water area, or a settlement catchment that becomes modelled isolated, with WorldPop grid cells. Sum cell values only as an **estimated resident distribution proxy**, date-labelled by the selected WorldPop release. It is not live presence, a count of trapped people, individual location, household vulnerability or an evacuation manifest.

WorldPop’s India constrained 100 m product is modelled people per pixel; the currently indexed R2025A release is labelled alpha and describes 3-arc-second (~100 m) cells [7]. For case-study reproducibility, pin the exact downloaded release and report its year. Use population as a queue multiplier, never as proof of people in flood water.

## Data ledger

| Layer | Access / status | MVP use | Important limitation |
|---|---|---|---|
| Sentinel-1 GRD | Copernicus Data Space STAC supports Sentinel-1 discovery; download needs a free account/OIDC token. Earth Engine has a daily updated, processed GRD collection [5, 8]. | Pre/post candidate-water signal. | Acquisition cadence and compatible pair availability constrain latency; radar is not water depth. |
| NRSC rapid mapping | Official 5 Sep and 11 Sep Vijayawada products are public [2, 3]. | Case-study reference/visual sanity check. | Not ground truth; NRSC explicitly excluded urban analysis in the 5 Sep product. Do not train or claim metric accuracy against it without a defined validation protocol. |
| PMGSY GeoSadak | Public under Government Open Data License [6]. | Rural road/habitation baseline, facility nodes. | Not live status; road completeness/topology around city/settlement connectors must be checked. |
| OpenStreetMap | Open data under ODbL; useful complementary road geometry. | Urban/local roads and bridges where available. | Volunteer completeness and tags vary; attribution/ODbL obligations apply. |
| WorldPop | Public, modelled gridded population [7]. | Resident-distribution proxy. | Not event-time occupancy or vulnerability. |
| Bhuvan NHP flood portal | Official portal offers flood hydrographs/simulations for Godavari and Tapi and shows event layers only during floods [9]. | Existing-solution comparison / analyst context. | It is not a general Vijayawada live API; do not scrape it or portray BaadhDrishti as an official replacement. |
| Field/authority reports | Required but no public real-time universal source verified in this research. | Confirm or overturn edge state. | Human verification is a hard operational dependency, not a data feed the MVP should pretend exists. |

## Scientific limits that the product must expose

1. **Urban SAR ambiguity is central, not a footnote.** Smooth water tends to produce low backscatter, but buildings/flooded built-up areas can produce double bounce and both dry/flooded urban scenes can be difficult to separate [4]. NRSC’s 5 September map excluded urban analysis [2]. Therefore do not use BaadhDrishti to label streets within dense Vijayawada as flooded or roads closed.
2. **Flooded vegetation, rough water and wet soil create omission/commission errors.** ESA training notes limitations for flooded/floating vegetation and the dependence on acquisition, landscape and weather [10].
3. **A single scene cannot distinguish permanent water from a new flood reliably.** A comparable dry reference and a permanent-water mask are required; ESA’s SNAP tutorial explicitly removes known water and uses elevation to reduce misclassification [11].
4. **SAR pixel size is not road status.** Sentinel-1 GRD imagery commonly has 10 m posting while effective resolution, processing and geolocation uncertainty mean narrow roads are sub-pixel or mixed. A crossing overlap is evidence to check, not an obstruction observation.
5. **No water depth or current.** Do not output either. The Bhuvan NHP portal’s modelled depth products are a distinct model/service for other basins; they cannot be inferred from this workflow [9].
6. **No rescue routing.** Remove suspected edges for analytic sensitivity; only verified closure/restriction reports may drive a responder route recommendation.
7. **Temporal mismatch matters.** Label scene acquisition time and baseline date; water can advance/recede between pass and response.

## Validation plan before any operational claim

The two-stage claim needs two separate validations.

### A. Inundation-candidate validation

- Freeze the AOI, image IDs, orbit filters, preprocessing, permanent-water mask, thresholds and morphology rules.
- Sample stratified points in open/rural, peri-urban, urban, wetland/vegetation and near-road contexts.
- Compare against time-aligned authoritative imagery, high-resolution post-event imagery if licensed, and field/agency evidence where available.
- Report confusion matrix, precision, recall and omission/commission errors **by land-cover stratum**, not one flattering global accuracy.
- Treat official rapid maps as reference context only unless their class definitions, timing and spatial uncertainty support a legitimate comparison.

### B. Reachability validation

- Freeze the road graph and selected staging point before reviewing reports.
- Assemble time-stamped independent road/bridge status evidence (district control room, NDRF/SDRF/agency updates or survey), with a clear hierarchy of authority.
- Measure edge-level precision/recall for `suspected disrupted`, then settlement-level precision/recall for `possible cut-off`.
- Audit every false cut-off: missing alternate lane, bad graph snap, bridge/elevated road, flood-mask false positive, wrong staging node, or late/incorrect road report.
- Report coverage: share of settlements that can be snapped plausibly and share of graph edges with a usable road class. “No route” has no value if mapping is incomplete.

Until those checks exist, the correct product wording is “verification priority”, never “cut-off village detected.”

## Build scope for a three-day hackathon

### Day 1 — reproducible replay

- Pick a **peri-urban/rural** AOI around Gollapudi–Jakkampudi–Rayanapadu rather than claiming street-level coverage for the city core.
- Discover a compatible Sentinel-1 baseline/crisis pair; record product IDs/times and use a fixed historical replay date.
- Ingest a small AOI road graph, settlement nodes and one nominated staging point.
- Display NRSC’s cited reference map link and a source drawer, without copying its output as ground truth.

### Day 2 — candidate and graph sensitivity

- Produce the A/B/C candidate layer with permanent-water and terrain exclusions.
- Create road-edge intersection evidence; run baseline vs suspected-edge-removed connectivity.
- Show each possible-cut-off settlement card with a “why this is flagged” panel and a reject/confirm edge control.

### Day 3 — truthfulness, demo and deployment

- Add a side-by-side pre/post radar view; make the date and `historical replay` label unmissable.
- Add population proxy only after pinning a WorldPop release and show it as a range/proxy.
- Record the required workflow: satellite candidate → suspected access disruption → modelled possible cut-off → human confirmation changes the result.
- Include a failure example (dense urban/ambiguous SAR class) where the tool refuses to make a road claim.

## AWS architecture appropriate to the actual claims

- **S3**: immutable, versioned input manifests, derived candidate rasters/vector tiles, road graph snapshot, and validation artefacts.
- **ECS/Fargate batch** or **AWS Batch**: containerised raster preprocessing and graph calculation; store exact container version and parameters in a manifest.
- **Step Functions**: explicit staged run: discovery → preprocess → candidate mask → road-intersection evidence → reachability → publish.
- **Lambda + API Gateway**: read-only query for settlement triage cards and a controlled endpoint for human confirmation state.
- **DynamoDB**: append-only/role-audited field-confirmation events; never overwrite raw detection evidence.
- **CloudFront / Amplify**: static analyst-facing map.

This is an AWS fit because it preserves reproducible, versioned evidence and separates batch geospatial computation from reviewed operational updates. Do not say “AI on AWS” unless a model is actually trained, evaluated and deployed.

## Novelty assessment

Flood mapping itself is not novel: NRSC/Bhuvan publish disaster and flood products [2, 9], and Sentinel-1 change detection is well documented [4, 5]. The defendable contribution is a transparent **uncertainty-first conversion of a satellite-water candidate into a field-verification queue for potentially lost network access**, coupled with reproducible evidence and an explicit refusal to make claims in ambiguous urban pixels. It should be pitched as a decision-support layer that complements official products, not as a replacement.

## Sources

[1] Andhra Pradesh State Disaster Management Authority, 2024 Andhra Pradesh floods impact/report material (PDF). https://apsdma.ap.gov.in/files/06104de92b01f273eead196a654d65dc.pdf

[2] NRSC/ISRO, “Flood Inundation Areas Surrounding Vijayawada, Andhra Pradesh, India,” map 2024/FL/AP/14/05092024; pre-event Sentinel-1A 20 Aug 2024, post-event TanDEM-X 5 Sep 2024. https://ndem.nrsc.gov.in/documents/Disaster_Document/2024/AP/apflood50dsc05092024_1800hrs/apflood50dsc05092024_1800hrs_map.pdf

[3] APSAC/NRSC, Vijayawada flood-inundation maps, 11 Sep 2024. https://apsac.ap.gov.in/wp-content/uploads/2024/09/ap_2024_11_09_map1.pdf

[4] Google Earth Engine, “Detecting Changes in Sentinel-1 Imagery (Part 4).” https://developers.google.com/earth-engine/tutorials/community/detecting-changes-in-sentinel-1-imagery-pt-4

[5] Google Earth Engine, Sentinel-1 SAR GRD data catalogue and preprocessing. https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD ; https://developers.google.com/earth-engine/guides/sentinel1

[6] Government of India, PIB, “Rural Connectivity GIS Data in Public Domain,” 28 Feb 2022. https://pib.gov.in/PressReleasePage.aspx?PRID=1800373 ; PMGSY GeoSadak open data: https://geosadak-pmgsy.nic.in/OpenData

[7] WorldPop, India constrained population, R2025A v1 metadata. https://hub.worldpop.org/geodata/summary?id=73812

[8] Copernicus Data Space Ecosystem, Sentinel-1 collection and STAC documentation. https://dataspace.copernicus.eu/data-collections/sentinel-data/sentinel-1 ; https://documentation.dataspace.copernicus.eu/APIs/STAC.html

[9] NRSC/Bhuvan National Hydrology Project Flood Geoportal. https://bhuvan.nrsc.gov.in/nhp/webgis-flood/map ; portal description: https://bhuvan.nrsc.gov.in/nhp/about-portal

[10] ESA, SAR flood-mapping training material. https://eoscience.esa.int/landtraining2018/files/materials/D5A1_LTC_theorical_YESOU_floods_final.pdf

[11] ESA SNAP, Sentinel-1 flood-mapping tutorial. https://step.esa.int/docs/tutorials/tutorial_s1floodmapping.pdf

## Research limitations

- This report verified public documentation and official case-study products; it did not download/process a specific Sentinel-1 pair, obtain field road-closure observations, or calculate an actual inundation/potential-cut-off total.
- Web retrieval was intermittently unavailable. Source claims are therefore limited to pages/documents successfully retrieved or directly cited above.
- A public road inventory is not a real-time routing feed. It must be corrected locally and independently verified before any operational use.
- The scope deliberately avoids a claimed live Vijayawada service: a historical replay is the appropriate hackathon demonstration unless a current, compatible acquisition and authorised ground validation are actually available.
