# BaadhDrishti — focused research: Vijayawada 2024 SAR flood replay and cut-off reachability

Research date: 9 October 2026. Scope is restricted to the seven requested questions. This is research only: no code and no architecture.

## Five-point summary — go/no-go and biggest risks

1. **GO, with a narrow claim:** produce a historical, satellite-derived *candidate* flood mask and a **possible cut-off / no mapped road path** verification queue. Do not call it live rescue routing, an official road-closure feed, or a count of trapped people.
2. **Vijayawada is a strong replay choice.** Earth Search returns the stated same-geometry pre/post scenes, and NRSC/APSAC plus International Charter Activation 907 provide unusually strong event-validation references.
3. **Main technical risk is urban SAR.** Open water is often dark, but flooded urban/vegetated pixels can be missed or confused because of double bounce. NRSC itself says its Vijayawada rapid map did not analyse urban areas. The demo should favour the peri-urban Gollapudi–Jakkampudi–Rayanapadu side and visibly flag dense urban cells.
4. **Main operational risk is facilities.** Current OSM has roads, named places and hospitals, but its `amenity=shelter` tag does not mean an official flood-relief camp. Say “nearest mapped hospital by remaining mapped road network”; show official shelter as unavailable unless a government camp list is available.
5. **Do not use raw Earth Search TIFF DN values in a threshold.** The Earth Search S1 GRD `vv`/`vh` assets are uint16 measurement files and include calibration LUT/XML assets. Convert/calibrate first. The actual replay has a **12-day** S1A gap, so do not pitch “six-day real-time monitoring.”

---

# 1. Competitors

## Short answer

Flood extent and exposed population are already supplied by major systems. What is not documented as their standard public output is the exact BaadhDrishti question: **after removing candidate-flooded OSM edges, which named settlements no longer have a mapped road path to a mapped hospital/staging point?** That is the narrow differentiation—not flood mapping itself.

## Evidence and links

| Competitor | Automatic flood extent? | Exposed population? | Cut-off settlements / road isolation / reachability? | Vijayawada 2024 map? |
|---|---|---|---|---|
| **Copernicus GFM** | Yes. Global near-real-time automated Sentinel-1 observed flood extent/water extent/reference-water/exclusion-mask products. | Yes. Affected Population is flood extent overlaid on GHSL 100 m population. | No documented graph/path-to-facility output. It includes OSM roads/railways for first infrastructure assessment, but not automatic settlement isolation. | **UNVERIFIED / not found** in this focused search. |
| **Copernicus EMS Rapid Mapping** | Yes, on-demand maps within hours/days after authorised activation. | Can provide exposure/assets depending on activation. | It provides flood extent and ancillary transport layers; no standard automatic road-network cut-off product was verified. | **No activation found** in focused portal search. |
| **Sentinel Asia** | Emergency satellite observations/value-added products for selected events. | Event-specific; no standard population product verified. | No standard reachability product verified. | **No product found** in reviewed 2024 portal/newsletters; absence is not proof none existed. |
| **UNOSAT** | Yes for many activations; uses Sentinel-1/other imagery. | Yes in many products using WorldPop; sometimes affected structures/cropland. | No verified standard road-graph isolation or hospital reachability analysis. | **No Vijayawada product found.** |
| **NRSC / APSAC / Bhuvan / NDEM** | Yes. NRSC/APSAC released rapid Vijayawada inundation maps. | Area/district statistics can be sent to agencies; no published Vijayawada population-exposure layer found. | Roads are reference layers; no cut-off/reachability analysis found. | **Yes — strongest validation reference.** |
| **Open-source SAR tools** — UN-SPIDER notebooks, GEE tutorials, GitHub S1 flood tools | Yes: threshold/change-detection masks. | Only when the user adds an overlay. | No built-in settlement cut-off workflow. | Not event-specific. |

Key sources:

* Copernicus GFM Product User Manual: https://extwiki.eodc.eu/gfm_assets/gfm4.0_pum_2025.pdf
* Copernicus GFM technical overview: https://extwiki.eodc.eu/GFM/PUM/TechnicalOverview
* Copernicus EMS overview: https://documentation.dataspace.copernicus.eu/Data/CopernicusServices/CEMS.html
* Copernicus EMS Mapping portal: https://mapping.emergency.copernicus.eu/
* Sentinel Asia emergency observations: https://sentinel-asia.org/EO/EmergencyObservation.html
* UNOSAT example of Sentinel-1 extent/population impact product: https://unosat.org/products/3992
* APSAC September 2024 flood map page: https://apsac.ap.gov.in/?page_id=7308

### Vijayawada reference material found

* APSAC/NRSC 6-Sep map: **Flood Inundation Areas Surrounding Vijayawada**. It uses 20-Aug Sentinel-1A as pre-event reference and 6-Sep TerraSAR-X as post-event imagery. NRSC calls it preliminary, warns that standing/rain water can be included, says no ground verification was done, and says urban inundation analysis was not part of the map because of high-resolution-data limits: https://apsac.ap.gov.in/wp-content/uploads/2024/09/AP_TERRASARX_6_sep_2024_sat_map.pdf
* APSAC/NRSC 11-Sep map series names Elaprolu, Kavuluru, Rayanapadu, Gollapudi, Jakkampudi, Ambapuram, Nunna, Vijayawada and Ramavarappadu: https://apsac.ap.gov.in/wp-content/uploads/2024/09/ap_2024_11_09_map1.pdf
* International Charter Activation 907, requested by ISRO 3 Sep 2024, states Budameru flooded about 40% of the city and stranded nearly 275,000 people: https://disasterscharter.org/activations/flood-in-india-activation-907-

## Implication for us

Pitch: “A transparent last-mile **verification-priority** layer over flood candidates.” Do not pitch “first flood map,” “better than NRSC,” or “AI rescue routing.” Use NRSC maps to test whether the broad candidate mask aligns with known flooded directions, while displaying NRSC’s own caveats.

---

# 2. Event choice — Vijayawada/Budameru, 31 Aug–2 Sep 2024

## Short answer

**Keep Vijayawada as the primary event.** It has a verified compatible SAR pair, official rapid-map references, named impacted areas, documented relief operations, and a real access-isolation story.

**Backup:** Assam’s second 2024 flood wave, ideally a selected Lakhimpur/Subansiri AOI in late June/early July 2024. ASDMA reports 3,769,861 affected people during the 16 June–11 September second wave, with an affected-population spike to 24.21 lakh on 5 July. Exact Earth Search pre/post scene IDs for the selected AOI are **UNVERIFIED** and must be queried before switching events: https://asdma.assam.gov.in/sites/default/files/swf_utility_folder/departments/asdma_revenue_uneecopscloud_com_oid_70/menu/document/assam_flood_memorandum_2024_.pdf

## Evidence: ground truth and response

| Fact | Evidence |
|---|---|
| Large parts of Vijayawada were under water from 31 Aug. | The Hindu reports the flood-affected exodus at Ajit Singh Nagar: https://www.thehindu.com/news/national/floods-in-andhra-pradesh-telangana-leave-thousands-homeless/article68597987.ece |
| Official/rapid-map place references include Gollapudi, Jakkampudi, Ambapuram, Nunna, Rayanapadu, Ramavarappadu, Elaprolu and Kavuluru. | APSAC/NRSC 11-Sep map cited above. |
| Charter scale is around 40% of city flooded and nearly 275,000 stranded. | International Charter Activation 907, cited above. |
| Statewide, reported government figures on 4 Sep were 644,000 affected and 42,707 people in 193 camps across seven districts. | Economic Times report: https://economictimes.indiatimes.com/news/india/andhra-pradesh-govt-provides-rs-5-lakh-ex-gratia-to-kin-of-20-flood-victims-relief-measures-continue/printarticle/113059468.cms |
| Vijayawada APSDMA-reported relief included 43,417 people moved to rehabilitation centres, 48 NDRF/SDRF teams and 197 medical camps; ministers/IAS/IPS officers worked ward-wise. | Business Standard report of official statement: https://business-standard.com/india-news/ndrf-begins-airdropping-food-packets-water-in-flood-hit-vijayawada-124090300350_1.html |
| Six helicopters and drones dropped food, water, milk, medicines and other essentials. | Same official-report coverage above. |
| Water duration has no single verified citywide number in retrieved sources. A report on 4 Sep quotes an Ajit Singh Nagar resident on a fourth day without power, but that is not a general water-duration measure. | Economic Times report cited above. |

**Numerical caution:** 275,000 stranded in Vijayawada, 43,417 moved to rehabilitation centres, and 644,000 affected statewide are different denominators. Never combine them.

## Implication for us

Use known place names as face-validity checks. If the flood candidate never reaches the broad areas named by official products/reporting, investigate before demo. Do not claim SAR derives exact water depth, days of standing water or trapped-person count.

---

# 3. Method — simple reliable Sentinel-1 GRD change detection

## Short answer

Recommended hackathon baseline:

1. Use the supplied same-geometry pair: 20-Aug and 1-Sep S1A, IW, descending, relative orbit 92, dual VV/VH.
2. Calibrate raw measurement values to sigma0 (σ⁰), remove noise, terrain-correct, and convert to dB only after calibration.
3. Apply identical moderate speckle reduction to both images.
4. Calculate a pre/post **linear-power ratio / log-ratio** or calibrated dB change; calculate Otsu threshold after exclusions within AOI.
5. Remove permanent water, steep slopes, small isolated components, and terrain artefacts; flag urban/vegetated/paddy contexts as low confidence.
6. Compare broad result against NRSC map references. Call output “candidate observed inundation,” not truth.

## Are Earth Search S1 GRD assets already calibrated sigma0?

**No, not directly.** Direct Earth Search STAC inspection of both user-specified items showed:

* product type `GRD`, IW, VV/VH, 10 m spacing, descending relative orbit 92;
* exact items: `S1A_IW_GRDH_1SDV_20240820T003107_20240820T003132_055289_06BD9B` and `S1A_IW_GRDH_1SDV_20240901T003107_20240901T003132_055464_06C415`;
* `vv` and `vh` data assets are `uint16` measurement TIFFs;
* separate `schema-calibration-vv/vh` calibration XML/LUT assets are supplied.

Therefore treat the TIFFs as raw measurement/amplitude values needing LUT calibration; do not threshold them as dB/sigma0. Direct unsigned HTTP range reads of the supplied post-event TIFF returned HTTP 206 during research, confirming read access at the time.

Earth Search explanation: https://element84.com/geospatial/introducing-earth-search-v1-new-datasets-now-available

Copernicus Sentinel Hub describes a different processed chain that applies calibration/noise removal and serves linear-power backscatter: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S1GRD.html

## Evidence + practical choices

| Issue | Evidence | Recommended choice |
|---|---|---|
| Preprocessing | UN-SPIDER lists orbit update, border/thermal noise removal, calibration, terrain correction and dB conversion. | Do all before comparison. |
| VV/VH | UN-SPIDER: VH is sensitive to surface change; VV is useful for open water/vertical structure. Automated study found VV slightly better under calm conditions. | VV primary for open-water candidate; retain VH as QA, not a complex new classifier. |
| Otsu | UN-SPIDER uses automatic Otsu/minimum methods but warns unbalanced histograms can fail. Change-detection comparison finds Otsu more liberal than Kittler–Illingworth. | AOI Otsu **after masks**; persist chosen threshold/provenance. Do not use universal fixed threshold. |
| Fixed threshold | UN-SPIDER GEE tutorial uses ratio >1.25 as an example; it says threshold is trial-and-error. A Mekong study found scene-dependent Otsu thresholds, around -22 dB during floods. | Use threshold only as event-specific baseline. Never hard-code 1.25/-22 dB as global rule. |
| Speckle | SAR needs speckle/noise management. | Same 3×3/5×5 median/Lee-style treatment on both images; record it. |
| Permanent water and paddy | UN-SPIDER masks water >10 months/year; paddy/seasonal water can look flooded. | Mask permanent water; tag seasonal/paddy areas lower confidence. |
| Shadow/terrain | UN-SPIDER example masks >5% slope; a published comparison uses CopDEM GLO-30 plus HAND/PLIA and majority filters. | Use `cop-dem-glo-30` slope mask; disclose the selected threshold and do not claim slope alone solves layover/shadow. |
| Urban flood | UN-SPIDER warns built-up and vegetated flood detection is difficult; NRSC excluded urban analysis in its 6-Sep map. | Emit `URBAN_SAR_LIMITATION`; never automatically call a city street flooded/closed. |

Method sources:

* UN-SPIDER Python SAR flood workflow: https://un-spider.org/advisory-support/recommended-practices/recommended-practice-flood-mapping/python-step-by-step
* UN-SPIDER GEE method: https://un-spider.org/advisory-support/recommended-practices/recommended-practice-google-earth-engine-flood-mapping/step-by-step
* UN-SPIDER limitations: https://un-spider.org/advisory-support/recommended-practices/recommended-practice-flood-mapping/in-detail
* Twele et al. (2016), automated Sentinel-1 flood chain: https://doi.org/10.1080/01431161.2016.1192304
* Change-detection comparison, Remote Sensing (2023): https://www.mdpi.com/2072-4292/15/5/1200
* Dynamic Otsu/VH flood mapping study: https://www.mdpi.com/2072-4292/14/22/5721

## Implication for us

Use a transparent rule-based baseline, not a black-box model. The validation/demo sequence should expose pre image → calibrated change score → exclusions → candidate mask → NRSC reference map. That is honest and reviewable.

---

# 4. Cut-off analysis — OSM roads, settlements and facilities

## Short answer

Simplest defensible definition: a settlement is **possible cut-off** if it had a mapped road path to a selected staging point/hospital before candidate-edge removal and no path after removal.

```
baseline: has_path(G, settlement, facility)
remove: road edges intersecting buffered candidate-water mask
result: baseline-connected AND no-path-after-removal = POSSIBLE_CUT_OFF
```

Use NetworkX for connected components and shortest path. OSMnx is optional for extraction/routing convenience.

## Evidence and coverage

| Layer | Finding | Implication |
|---|---|---|
| Roads | Geofabrik India/central-zone extract is public: `https://download.geofabrik.de/asia/india/central-zone-latest.osm.pbf` | Current baseline road graph is feasible; it is not a 2024 road-status feed. |
| Settlements | OSM `place=*` may be a centre point or full area; boundaries are inconsistent. | Use named settlement/colony **centres**, not claimed colony boundaries. |
| Current Vijayawada OSM check | A direct current Overpass query over 16.45–16.75 N, 80.45–80.85 E found 163 villages, 127 neighbourhoods and 14 suburbs; sample names include Rayanapadu and Gannavaram. | Enough for a demonstration, but present it as current OSM—not 2024 authoritative mapping. |
| Hospitals | OSM uses `amenity=hospital` plus optional `healthcare=*`/`emergency=*`. Query found 396 hospital-tagged features in broad AOI. | “Nearest mapped hospital” is usable. Capacity/open status/flood operability are **UNVERIFIED**. |
| Shelters | OSM `amenity=shelter` commonly means physical shelter, often a bus-stop structure; query found one shelter feature in broad AOI. | Do not call it a relief camp. Official shelter location remains **UNVERIFIED**. |

Sources:

* Geofabrik India: https://download.geofabrik.de/asia/india.html
* OSM place tags: https://wiki.openstreetmap.org/wiki/Place
* OSM healthcare tags: https://wiki.openstreetmap.org/wiki/Healthcare
* OSM shelter key: https://wiki.openstreetmap.org/wiki/Key:shelter

## Critical controls

* A flood-mask/road intersection is **suspected disruption**, not road closure.
* Preserve bridge/tunnel/culvert edges as `needs review`: water under a bridge is not necessarily impassable road.
* “No mapped road path” is not “rescuers cannot reach it”; unmapped tracks/boats/emergency routes may exist.
* Compute connected components first, then shortest paths only for surviving components.

## Implication for us

Priority-list row:

`rank | named place | modelled resident proxy | candidate flooded road edges | NO MAPPED ROAD PATH / PATH EXISTS | nearest mapped hospital name + route distance OR none in component | uncertainty flags | action: verify by ward/boat team`.

Do not show a “nearest shelter” value without official camp data.

---

# 5. Population — WorldPop and GHSL

## Short answer

Use **GHSL GHS-POP R2023A, E2020, 100 m** as primary. It is directly verified, licensed CC BY 4.0 and is the population family used by Copernicus GFM. WorldPop is an acceptable alternative, but direct exact India-total 2020 constrained TIFF URL was not verified and a previously guessed path returned HTTP 404.

## Evidence + links

| Dataset | Verified access | Resolution / licence | Implication |
|---|---|---|---|
| WorldPop constrained India 2020 | Product portal: https://hub.worldpop.org/geodata/summary?id=49992 ; age/sex India 2020: https://hub.worldpop.org/geodata/summary?id=50436 | ~100m (3 arcsec), WGS84, people per pixel; constrained WorldPop documentation identifies CC BY 4.0. | Product/licence verified; **exact direct total-population India TIFF URL UNVERIFIED**. Retrieve filename from portal/manifest rather than guess. |
| GHSL GHS-POP R2023A | Official: https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php ; download portal: https://ghsl.jrc.ec.europa.eu/download.php | 100m/1km/3 arcsec/30 arcsec; E1975–E2020 estimates, E2025/E2030 projections; CC BY 4.0. | **Use E2020 for a 2024 historical replay.** |

WorldPop CC BY documentation: https://developers.google.com/earth-engine/datasets/catalog/WorldPop_GP_100m_pop_age_sex_cons_unadj

GHSL data-package licence: https://human-settlement.emergency.copernicus.eu/documents/GHSL_Data_Package_2023.pdf

## Implication for us

Label result exactly as: **“modelled resident population in candidate inundated/isolation-associated 100 m cells (2020 estimate)”**. Round values (e.g., nearest 100). Never call it trapped population, current presence, evacuation manifest, or vulnerability assessment.

---

# 6. Sentinel-1 revisit

## Short answer

Pitch wording:

> “When a Sentinel-1 acquisition is available, BaadhDrishti can produce an update from that acquisition. A two-satellite Sentinel-1 constellation has a nominal six-day exact-repeat cycle; availability over one Indian AOI depends on acquisition plan, coverage, orbit direction and publication. It is not continuous monitoring.”

## Evidence

* Sentinel-1B failed in Dec 2021. Sentinel-1C launched 5 Dec 2024; Sentinel-1D launched 4 Nov 2025.
* ESA/SentiWiki: one satellite has 12-day repeat; two satellites have nominal six-day exact-repeat, with actual rate varying by latitude/planning.
* The selected Vijayawada replay is S1A-only, **20 Aug to 1 Sep = 12 days**. That is the actual case-study cadence.

Sources:

* ESA facts: https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-1/Facts_and_figures
* SentiWiki mission: https://sentiwiki.copernicus.eu/web/s1-mission

## Implication for us

Display scene time and `image age`. Say “acquisition-triggered update,” not real time or guaranteed six-day flood detection.

---

# 7. Real user workflow — Collector, SDMA and NDRF

## Short answer

The intended user needs a map plus a short field-verification list, not an autonomous dispatch engine. NDRF flood SOP asks for affected area, population yet to evacuate, priority rescue places, immediate-rescue areas, shelters/relief/medicine locations, communication mode, resource contacts and active hospital list. It says Collectors/DCs/DMs can request NDRF response.

Vijayawada 2024 reporting confirms ward-wise official relief activity and use of camps, medical camps, NDRF/SDRF, helicopters and drones. That supports a **ward/place priority list + static shareable brief**, not a consumer navigation tool.

## Evidence + links

* NDRF flood SOP: https://ndrf.gov.in/sites/default/files/FLOOD.pdf
* NDMA preparedness guidance calls for GIS plot of vulnerable localities, roads, hospitals/PHCs, relief camps and logistics: https://ndma.gov.in/sites/default/files/PDF/Review%20of%20Preparedness%20for%20the%20South%20West%20Monsoon%20Season%20Tropical%20Cyclones.pdf
* Vijayawada ward-wise relief/airdrop evidence: Business Standard link in Section 2.

## Recommended output format

1. **Map:** candidate flood mask; excluded/ambiguous zones; suspected disrupted edges; named places; mapped hospitals; image dates.
2. **One-page PDF/CSV list suitable for WhatsApp forwarding:** rank, place, 2020 population proxy, suspected road-edge count, `NO MAPPED ROAD PATH` / `PATH EXISTS`, nearest mapped hospital/no facility in component, uncertainty flags, and `verify by ward/boat team` action.

## Implication for us

The final demo should end with five ranked verification rows. It should show that human confirmation changes the result. It must not route responders through a possibly flooded network.

---

# Decisions to take after research

1. Approve the claim boundary: “candidate road isolation for verification,” not detected cut-off people/rescue routing.
2. Approve Vijayawada primary event and NRSC/APSAC maps as qualitative validation references.
3. Choose GHSL E2020 as population primary; use WorldPop only after official direct-file retrieval.
4. Remove official-shelter claim from MVP unless an authoritative camp list is obtained.
5. Freeze a road-edge removal rule, bridge/tunnel review rule, and uncertainty labels before implementation.
6. Approve baseline: calibrated sigma0 VV change/ratio + AOI Otsu + permanent-water/slope/component masks; keep VH as QA.
7. Require named-area/NRSC face-validity checks and visible failure examples in urban SAR zones.
8. Keep Assam Lakhimpur/Subansiri as backup only after exact compatible Earth Search scene IDs are verified.

## Limitations

* Current OSM query is not a historical 2024 OSM snapshot.
* Public road layers are not live road-closure feeds.
* Direct S3 range read worked during research; runtime must still implement access/error handling.
* This research establishes a defensible baseline and validation references; it does not prove accuracy for a chosen threshold.
