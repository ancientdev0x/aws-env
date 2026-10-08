# Research Round 2 — verified-data and novelty ranking

Research date: 8 October 2026 (hackathon window: 8–11 October 2026)

## Decision first

The hard filter was applied strictly: no manual entry, no field work, no marketplace/network dependency, and the MVP must run from public/live data. “Verified” below means this research pass opened the provider page or endpoint and confirmed the stated access terms; it does **not** mean that an unauthenticated third-party mirror is an official API. “UNVERIFIED” means a useful-looking source exists but a stable public machine endpoint, licence, or geographic record set was not established.

| Rank | Idea | Track | Novelty against existing products | Data access | Impact / decision | 3-min wow moment | Total / 35 |
|---:|---|---|---|---|---|---|---:|
| 1 | **BaadhDrishti** | Heat & Water | Moderate: government portals publish flood maps, but a transparent, reproducible Sentinel-1 change map plus exposure count is still a useful prototype | **Verified core imagery; verified public population API; event-dependent** | Disaster/ward officer prioritises the first 10 localities for verification/relief | Slider: pre-flood SAR → post-flood water mask → buildings/people exposed | **26** |
| 2 | **Dhuaan Alert** | Air | Weak–moderate: IITM AQEWS already publishes Delhi AQI and meteorology forecasts; the defensible gap is an auditable fire-wind evidence card, not another AQI forecast | **Verified FIRMS and ERA5 archive; CPCB programmatic access needs a key** | School/household changes outdoor activity and filtration preparation 24–48 h ahead | Re-run November 2024: upwind-fire/wind score appears before observed PM/AQI rise | **25** |
| 3 | **ThandaShehar** | Heat & Water | Moderate at ward-action level, but heat maps and block-scale tools already exist | **Verified Landsat source, but requester-pays; population and ward boundary pipeline needs validation** | City NGO/ward team chooses a small number of cooling/shade interventions | “Hottest × most populated” priority map and a concrete cool-roof/tree target | **23** |
| 4 | **SolarChhat** | Waste & Energy | Weak: official ISRO calculator and many commercial calculators already estimate rooftop output/payback | **Verified NASA POWER; building-footprint coverage and tariff/subsidy computation are not verified as APIs** | Household decides whether to start official PM Surya Ghar application | Click a roof, see conservative potential and official next step—not a sales lead | **20** |
| 5 | **Parali Radar** | Air | Moderate concept, but weakest under the hard filter because CRM-centre and offtaker coordinates are not verified as a national live public dataset | **Verified FIRMS only; facility/machine locations UNVERIFIED** | District programme manager targets outreach/logistics, not an individual farmer | Fire clusters + nearby verified handling capacity—only if authoritative locations are obtained | **16** |

### Scoring method

Each idea is scored 1–5 on README criteria: Idea & Impact, Built on AWS/open data fit, Design & Usability, Execution within four days without manual inputs, and video “wow”. The last column is their sum. A concept can have a strong environmental problem and still score low on execution if a required data layer is inaccessible.

## Cross-cutting reality check: what is live on 8–11 October?

- **Delhi air / fires:** live enough to demonstrate feeds, but not peak-season proof. IITM AQEWS’s live 8 October bulletin reported Delhi AQI 136 (Moderate) at 4 PM on 7 October and forecast Moderate conditions through 11 October. FIRMS will show live detections if present, but the Punjab/Haryana post-paddy-burning signal normally strengthens later in October/November. Use a live status panel plus a historical November 2024 backtest; do not promise a smoke event during the hackathon.
- **Flood:** October is post-monsoon/cyclone season on parts of India, but a flood is not guaranteed at the chosen AOI and Sentinel-1 only delivers when a scene is acquired. The demo must support an archive replay. This is genuine remote/public data, not synthetic data.
- **Solar:** irradiance and satellite sources are available year-round. October can show recent NASA POWER values, but rooftop output remains an estimate without roof geometry, shading, tariff and consumption data.
- **Urban heat:** Landsat continues to acquire scenes, but cloud-free thermal scenes, not a real-time heat emergency, determine availability. October is generally a weaker Indian heatwave story than April–June. Frame as planning, not heat-warning.
- **Parali:** the seasonal hook is real but is still early on 8–11 October. Its essential facility-location layer fails the public-data-only filter today.

## 1. BaadhDrishti — radar flood extent and affected-population screen

### User, decision and bounded impact

User: a district emergency cell, local relief NGO, or ward control room. Decision: after a cyclone/flood alert, which localities should be verified and supplied first. The app must output *screening priority*, not a declaration that every dark radar pixel is flooded and not an official damage estimate.

The measurable output is: flooded-area estimate, count of intersected building/population pixels, number of priority wards, source scene IDs and confidence flags. A useful demo is a historical Indian flood with before/after Sentinel-1 scenes; no resident reports are required.

### Existing solutions / novelty

| Existing solution | What it does | Gap relative to this proposal |
|---|---|---|
| NRSC/Bhuvan Disaster Services — https://bhuvan-app1.nrsc.gov.in/disaster/disaster/ | National remote-sensing portal publishes disaster/flood products and state-level aggregated historic flood maps. | This is authoritative and reduces novelty. BaadhDrishti must not position itself as replacing NRSC. Its only plausible gap is a fast, reproducible open workflow that shows source scenes, threshold uncertainty and a local exposure triage layer. |
| Bhuvan Spatial Flood Early Warning System — https://bhuvan.nrsc.gov.in/nhp/webgis-flood/map | Flood geoportal advertises discharge hydrographs, spatial inundation maps and basin layers. | Same conclusion: official mapping exists. Do not claim “India’s first flood map.” |
| Sentinel-1 flood workflows in Google Earth Engine / open tutorials | Common before/after SAR flood-detection workflow. | The analysis itself is not novel. The product value must be transparent decision cards and source provenance. |

Novelty verdict: **moderate only if the product is a transparent decision workflow; weak if it is just a flood raster/map.**

### Data-access ledger

| Source | Exact access / sample request | Cost, key, refresh, licence | Status and MVP use |
|---|---|---|---|
| Sentinel-1 GRD COG, AWS Open Data | `aws s3 ls --no-sign-request s3://sentinel-s1-l1c/` (bucket `sentinel-s1-l1c`, eu-central-1); STAC link is listed at https://registry.opendata.aws/sentinel-1/ | No AWS account required for the listed CLI access; new data generally within hours of Copernicus availability; Sentinel terms are free/full/open. | **VERIFIED.** SAR sees through cloud; 6-day constellation revisit stated by registry. Use two archived scenes for one declared event. |
| Population | WorldPop REST example: `https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/IND/ind_ppp_2020_constrained.tif` | Public download; licence/version must be displayed from WorldPop metadata. Not live; annual/gridded exposure denominator. | **UNVERIFIED licence in this pass.** Can use only after checking the precise product metadata; do not call it real-time. |
| Buildings / boundaries | Overture Maps releases (https://docs.overturemaps.org/), or a provider’s open administrative boundaries | Versioned releases rather than incident-live data; exact India coverage/licence and stable API must be checked for chosen AOI. | **UNVERIFIED for a nationwide production claim.** Restrict demo to one AOI with committed, downloaded open boundary data. |
| Bhuvan flood layers | Portal: https://bhuvan-app1.nrsc.gov.in/disaster/disaster/ | Public portal, but no stable documented REST/WMS endpoint verified in this pass. | **UNVERIFIED as machine input.** Cite/compare visually; do not scrape it into the app. |

Natural AWS fit: Sentinel-1 is already an AWS Open Data Registry dataset; a small **S3 + Lambda** job can preserve scene IDs and the derived GeoJSON/COG.

### Scores

- Idea & Impact **5/5** — converts imagery into a specific post-event triage decision.
- Built on AWS **5/5** — directly uses AWS Open Data Sentinel-1, satisfying the README’s open-source/AWS route.
- Design & Usability **4/5** — a simple before/after/exposure map is understandable, but uncertainty must be prominent.
- Execution **4/5** — archive replay is viable; robust water classification/exposure validation is not a four-day operational system.
- Video wow **5/5** — visual scene-to-priority transformation is compelling.

## 2. Dhuaan Alert — fire–wind evidence cards for Delhi preparedness

### User, decision and bounded impact

User: Delhi/NCR school administrator, parent, or facilities manager. Decision: prepare indoor activity/filtration and communicate a precautionary plan when a regional smoke-risk signal is elevated. It must never claim a particular fire *caused* a Delhi PM2.5 spike or replace official AQI health guidance.

A measurable backtest: for each daily 2024 fire/wind score, compare next 24/48-hour score bins against observed Delhi AQI/PM2.5. Report precision/recall/calibration, including false positives—not a single impressive case.

### Existing solutions / novelty

| Existing solution | What it does | Gap relative to this proposal |
|---|---|---|
| IITM Air Quality Early Warning System for Delhi (AQEWS) — https://ews.tropmet.res.in/ | Official IITM/MoES service publishes observations, AQI outlook, meteorological narrative, ventilation index and forecast analysis/verification. On 8 Oct it publishes the 8–11 Oct forecast. | A generic “1–2 day Delhi smoke warning” is **already covered in substance**. The only honest differentiator is an auditable, source-level regional-fire/wind explanation card and transparent retrospective score validation. |
| SAFAR — https://safar.tropmet.res.in/ | IITM’s air-quality/weather observation and forecast system, including current and short-horizon forecast products. | Not a gap for an AQI dashboard or forecast. |
| CPCB CAAQMS / National AQI — https://app.cpcbccr.com/AQI_India/ | Official current monitoring/AQI reference. | Use as reference observation, not a competitor to “beat.” |
| UrbanEmissions data-access guide — https://urbanemissions.info/blog-pieces/resources-how-to-access-aqdata-in-india/ | Documents Indian monitoring sources and access paths. | It is a data guide, not this product; nevertheless it confirms that data access needs care. |

Novelty verdict: **weak–moderate.** Build only if the team can show quantified historical calibration and visibly defer to AQEWS. Without that, it is a duplicate forecast dashboard.

### Data-access ledger

| Source | Exact access / sample request | Cost, key, refresh, licence | Status and MVP use |
|---|---|---|---|
| NASA FIRMS area API | Format: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/[MAP_KEY]/VIIRS_SNPP_NRT/73,28,78,33/5` ; historical form adds `/YYYY-MM-DD`. Documentation: https://firms.modaps.eosdis.nasa.gov/api/area/ | Free **MAP_KEY required**. API documentation says area calls cover 1–5 days; NRT, standard-processing sources available; NRT is typically available within 3 hours (NASA FIRMS documentation) and products have different processing characteristics. | **VERIFIED.** Register and use server-side key; do not commit it. For historical dates, confirm product availability first at `https://firms.modaps.eosdis.nasa.gov/api/data_availability/`. |
| ERA5 wind archive — maintained AWS mirror | `aws s3 ls --no-sign-request s3://nsf-ncar-era5/` (us-west-2); https://registry.opendata.aws/nsf-ncar-era5/ | No AWS account required for listed CLI access. Hourly 0.25° data; monthly release with 3–4 month lag; UCAR terms: https://www.ucar.edu/terms-of-use/data | **VERIFIED.** Suitable for November 2024 backtest, not a 1–2 day operational forecast. |
| Forecast wind for live warning | AQEWS bulletin URL above provides human-readable forecast; a clean documented public numerical IMD forecast API was not verified. | No confirmed stable API / licence. | **UNVERIFIED.** Do not promise automated live 48-hour wind forecast. For demo, display official AQEWS bulletin link and historical ERA5 backtest. |
| CPCB real-time AQI | Official catalog resource ID: `3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69`; sample pattern: `https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69?api-key=[KEY]&format=json&limit=10` | data.gov.in API key required; portal says the data are live field-instrument data and may have abnormal values. Exact historical retention/API update schedule was not verified. | **VERIFIED key requirement; UNVERIFIED for Nov-2024 retrieval.** Capture current snapshots yourself; do not assume historical API access. |
| November 2024 observed AQI/PM2.5 | CPCB historical download endpoint was not verified; OpenAQ historical coverage/API eligibility must also be checked at implementation time. | Unknown for required dates/stations. | **UNVERIFIED.** Backtest is only credible after acquiring and freezing a legal, timestamped observation dataset. |

### Required literature check: trajectory plausibility is not validation

A 2020 peer-reviewed study, Nair et al., “Assessment of contribution of agricultural residue burning on air quality in Delhi using … HYSPLIT,” *Atmospheric Environment* 224, 117185, doi:10.1016/j.atmosenv.2020.117185, uses HYSPLIT trajectories to show north-westerly flow intersecting residue-burning regions. A newer satellite/trajectory analysis (Kotrike et al., 2026, https://pmc.ncbi.nlm.nih.gov/articles/PMC12823738/) reports clusters of trajectories from active-burn zones intersecting Delhi within roughly 36 hours.

That supports the **physical plausibility** of a simple wind/trajectory screen. It does **not** validate a specific threshold as a reliable PM2.5-spike predictor: emissions, boundary-layer height, dust, traffic, humidity and local sources confound the association. The product must run its own dated hold-out backtest and label output “risk signal, not attribution.”

### Scores

- Idea & Impact **4/5** — exposure-preparation decision is concrete but official forecasts already exist.
- Built on AWS **4/5** — AWS ERA5 registry mirror is a real fit; live forecast layer is not verified.
- Design & Usability **4/5** — one evidence card can be clearer than a technical bulletin.
- Execution **3/5** — requires source/key setup and an actual historical CPCB/PM dataset before making performance claims.
- Video wow **5/5** — November-2024 replay can be striking if backtest metrics are honest.

## 3. ThandaShehar — heat-priority planning map

### User, decision and bounded impact

User: municipal heat-action-plan partner, NGO or ward planner. Decision: which wards should receive a limited cool-roof/shade/water-point assessment first. Rank a ward by satellite land-surface-temperature anomaly times a clearly named population/exposure proxy. Land-surface temperature is **not** human air temperature and cannot diagnose personal heat risk.

### Existing solutions / novelty

| Existing solution | What it does | Gap relative to this proposal |
|---|---|---|
| WRI Cool Cities Lab — https://www.wri.org/news/release-new-global-platform-maps-urban-heat-risks | Global 2026 platform maps heat risks down to block level and helps compare cooling interventions. | Makes a generic priority map less novel. |
| SEEDS India / Microsoft “Sunny Lives” reporting — https://www.preventionweb.net/news/india-using-ai-and-satellites-map-urban-heat-vulnerability | Reports an AI/satellite approach for Indian heat vulnerability. | Evidence that Indian hyperlocal heat mapping already exists. |
| Open-source/GitHub heat-map projects, e.g. SuryaDrishti — https://github.com/Nitanshu715/SuryaDrishti | Landsat urban-heat platform example. | Do not claim technical novelty for Landsat LST mapping. |

Novelty verdict: **moderate only if linked to an intervention queue, budget constraint and uncertainty; otherwise weak.**

### Data-access ledger

| Source | Exact access / sample request | Cost, key, refresh, licence | Status and MVP use |
|---|---|---|---|
| USGS Landsat Collection 2 on AWS | `aws s3 ls --request-payer requester s3://usgs-landsat/collection02/`; registry: https://registry.opendata.aws/usgs-landsat/ | **Requester Pays**; AWS account/billing needed to retrieve objects directly. New scenes daily. USGS says no restrictions on downloaded Landsat redistribution, with source acknowledgement requested. | **VERIFIED.** This violates “no card/no bill” if direct bucket route is used; use an alternate free public delivery only after independently verifying it. |
| Landsat STAC/metadata | Registry provides a STAC catalog link for Collection 2. | Catalog is documented, but actual asset retrieval remains requester-pays under this registry record. | **VERIFIED limitation.** |
| Population and ward polygons | WorldPop and OSM/official municipal boundaries | Exact licence, version, and all-India ward coverage were not verified. | **UNVERIFIED.** A one-city demo can be built only after freezing a licensed boundary source. |

Natural AWS fit: **USGS Landsat AWS Open Data** is natural, but its requester-pays condition is a material hackathon constraint.

### Scores

- Idea & Impact **4/5** — allocation of scarce cooling resources is meaningful.
- Built on AWS **3/5** — direct registry imagery is requester-pays, undermining the no-account path.
- Design & Usability **4/5** — priority map + intervention card is legible.
- Execution **4/5** — historical single-city analysis is feasible, but not real-time and needs validated boundaries/population.
- Video wow **4/5** — visual, but less immediate than flood imagery.

## 4. SolarChhat — conservative rooftop solar discovery

### User, decision and bounded impact

User: a household deciding whether to submit an official rooftop-solar application. The tool changes a vague “is solar worth it?” decision into a conservative range plus a link to the official PM Surya Ghar process. It must not quote a binding subsidy, tariff, engineering design, roof safety or payback without location-specific verified inputs.

### Existing solutions / novelty

| Existing solution | What it does | Gap relative to this proposal |
|---|---|---|
| ISRO Solar Calculator — https://www.isro.gov.in/Atmanirbhar/Solar_Calculator.html | Official page describes estimating monthly rooftop energy generation for citizens. | Direct functional overlap. |
| National Portal solar-rooftop calculator — https://www.india.gov.in/service/solar-roof-top-calculator | Calculator based on budget, space or kW requirement. | Direct functional overlap. |
| Commercial examples: MYSUN / Waaree / Rayzon calculators | System-size, generation, saving and payback estimates. | Market is crowded; a generic calculator has **weak novelty**. |
| CSTEP CREST/BESCOM rooftop mapping — https://cstep.in/real-world/unlocking-indias-solar-potential | Detailed rooftop maps for Bengaluru using LiDAR. | A serious local competitor/data precedent; raw satellite footprint inference will be less accurate. |

Novelty verdict: **weak.** A legitimate differentiator would be showing confidence/range and routing to official scheme steps, but that is presentation differentiation, not a new capability.

### Data-access ledger

| Source | Exact access / sample request | Cost, key, refresh, licence | Status and MVP use |
|---|---|---|---|
| NASA POWER solar irradiance | Live example opened successfully: `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=ALLSKY_SFC_SW_DWN&community=RE&longitude=77.1025&latitude=28.7041&start=20261001&end=20261005&format=JSON` | No key observed; daily API returns `kW-hr/m²/day`; current daily values can include fill value `-999` before processing. NASA POWER terms/citation must be followed. | **VERIFIED.** Good for an irradiance baseline, not roof-specific shade. |
| PM Surya Ghar portal | https://pmsuryaghar.gov.in/ | Official portal exists; a public calculator/subsidy API, stable machine endpoint and versioned subsidy table were not verified. | **UNVERIFIED as API.** Link users to portal; do not scrape or hard-code changing subsidy/tariff claims. |
| Building footprints | Overture/OSM or local government data | Coverage, geometry quality, licensing and rooftop suitability not verified for selected Indian city. | **UNVERIFIED.** Roof outlines alone cannot infer shading, structural load or ownership. |
| Optical imagery | Sentinel-2 L2A: `aws s3 ls --no-sign-request s3://sentinel-s2-l2a/`; registry: https://registry.opendata.aws/sentinel-2/ | Public/no account required for L2A listing; new scenes within hours of Copernicus availability; 10 m pixels are too coarse for individual roof geometry. | **VERIFIED access, inadequate as sole roof-geometry source.** |

Natural AWS fit: **S3** for cached NASA POWER responses/assumptions; AWS Open Data Sentinel-2 is a contextual layer, not a reliable roof estimator.

### Scores

- Idea & Impact **3/5** — decision support is useful but incumbents already handle it.
- Built on AWS **4/5** — clean NASA POWER + public Sentinel-2 integration.
- Design & Usability **5/5** — clear roof-click/user journey.
- Execution **4/5** — a conservative prototype is easy; a credible per-roof estimate is not.
- Video wow **4/5** — attractive visual, low surprise relative to competitors.

## 5. Parali Radar — fire clusters versus residue-handling capacity

### User, decision and bounded impact

Proposed user: district agriculture/CRM programme official. Decision: target a block for awareness/logistics where fire detections and verified residue-management capacity are mismatched. It must not name/penalise individual farmers from satellite detections and must not claim that a nearby plant can accept residue without confirmed capacity/contracts.

### Existing solutions / novelty

| Existing solution | What it does | Gap relative to this proposal |
|---|---|---|
| Punjab Remote Sensing Centre crop-data app — https://prsc.punjab.gov.in/Web_App | Punjab crop datasets generated from remote sensing. | Demonstrates government spatial agriculture capability already exists. |
| Digital Platform for Farm Mechanization and Technology / CRM guidelines — https://agrimachinery.nic.in/Guidelines_CRM2024 | CRM programme rules describe beneficiary/supply-chain roles. | This is policy/programme infrastructure, not a live public geospatial inventory. |
| PEDA Bio-CNG/CBG projects — https://www.peda.gov.in/bio-cbg-compressed-biogas-projects | Punjab agency describes allocated/operational CBG projects. | A project list is not verified as a full geocoded, capacity/current-acceptance API. |
| CEEW, “How can Punjab end stubble burning…” — https://www.ceew.in/publications/how-can-punjab-end-stubble-burning | Analyses residue-management pathways at state scale. | Shows the problem is broader than spatial matching alone. |

Novelty verdict: **moderate product idea, but infeasible under this task’s public-live-data-only filter.**

### Data-access ledger

| Source | Exact access / sample request | Cost, key, refresh, licence | Status and MVP use |
|---|---|---|---|
| NASA FIRMS detections | Same verified FIRMS endpoint as Dhuaan Alert; Punjab/Haryana example box: `73,28,78,33`. | Free MAP_KEY; 1–5 day queries; NRT/standard products as documented. | **VERIFIED.** Fire point is a detection, not a verified residue-burning incident. |
| CRM machine/custom-hiring centres | Central CRM guidelines/portals found, but no stable national open endpoint or downloadable geocoded inventory was verified. | Unknown. | **UNVERIFIED / hard blocker.** |
| Biomass, bio-CNG, power plant locations/capacity/acceptance | PEDA/state/project pages exist; no public, complete, geocoded, current intake API verified. | Unknown. | **UNVERIFIED / hard blocker.** |
| Crop type / residue likelihood | PRSC has a crop-data web app, but an open reproducible endpoint/licence for this feature was not verified. | Unknown. | **UNVERIFIED.** |

Natural AWS fit: no AWS Open Data dataset solves the missing authoritative facility layer. Storing FIRMS only in S3 does not solve the feasibility problem.

### Scores

- Idea & Impact **4/5** — capacity mismatch is an operationally meaningful framing.
- Built on AWS **2/5** — FIRMS integration alone is not sufficient, and no natural verified AWS dataset fills the key gap.
- Design & Usability **3/5** — district map could work, but audience is specialised.
- Execution **2/5** — mandatory facility data is unverified; prohibited manual curation cannot repair it.
- Video wow **5/5** — would be powerful, but only with trustworthy locations.

## Recommendation

Build **BaadhDrishti**, with a single historical Indian flood/cyclone replay and deliberately narrow claim: “a transparent Sentinel-1 screening map that identifies candidate high-exposure areas for verification.” It has the best balance of real public data, a decision a remote team can demonstrate without field work, clear AWS Open Data provenance, seasonally plausible context, and a visual three-minute narrative.

Do not build Parali Radar unless an authoritative, public, geocoded CRM-centre and offtaker dataset is obtained before coding. Do not build a generic SolarChhat calculator: official and commercial calculators already cover the core feature. Dhuaan Alert is the fallback only if the team first obtains a dated Nov-2024 observed CPCB/PM dataset and reports real backtest metrics; AQEWS makes an unvalidated 1–2 day forecast a weak novelty claim.

## Source and verification notes

1. AWS Sentinel-1 registry (access path, timing, licence): https://registry.opendata.aws/sentinel-1/
2. AWS Sentinel-2 registry: https://registry.opendata.aws/sentinel-2/
3. AWS USGS Landsat registry (including Requester Pays): https://registry.opendata.aws/usgs-landsat/
4. AWS maintained NSF/NCAR ERA5 registry: https://registry.opendata.aws/nsf-ncar-era5/
5. NASA FIRMS Area API: https://firms.modaps.eosdis.nasa.gov/api/area/
6. NASA POWER Daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
7. IITM Delhi AQEWS: https://ews.tropmet.res.in/
8. CPCB real-time AQI catalogue: https://data.gov.in/catalog/real-time-air-quality-index
9. Hackathon eligibility/judging basis: `README.md` in this repository.

Limitations: provider endpoints, data retention and programme pages can change. No endpoint with a secret/key is placed in the repository. “Verified” conclusions are scoped to the source/access evidence above; unverified items are intentionally not converted into requirements by assumption.
