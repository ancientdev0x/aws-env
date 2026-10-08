# Bharat Builds Tour — Environmental Hacks: Research V2

Research date: 8 October 2026. This report supersedes the prior V2 draft.

## Hard filter and terminology

The team is remote in Kharagpur. A viable MVP must run without manual data entry, field work, a partner network, marketplace operations, or unverified private datasets. “Verified” means the publisher documentation was inspected and, where practical, the example endpoint was requested on 8 October. “UNVERIFIED” means a useful site exists but a stable machine interface, licence, or required data layer was not established; it cannot be critical-path data.

Scores are /5 against the README: Idea & Impact (I), Built on AWS (A), Design & Usability (D), Execution in three days using the hard filter (E), and 3-minute demo wow (W). Total /25.

## Ranking

| Rank | Idea | Track | Novelty (against existing solutions) | Data access | Impact / decision | Wow moment | Total |
|---:|---|---|---|---|---|---|---:|
| 1 | **ThandaShehar** | Heat & Water | Moderate: heat/LST maps exist, but a source-linked heat × population intervention queue is less directly served by the products checked. | **Verified core:** Landsat ST, WorldPop, Overture buildings. Official Delhi ward boundary download is UNVERIFIED; use grid cells. | Planner selects first cells for shade/cooling-access inspection before summer. | 30 m hot-surface scene becomes a ranked “people exposed” map. | **18** |
| 2 | **BaadhDrishti** | Heat & Water | Moderate-low: Bhuvan already publishes inundation products; transparent processing and an uncertainty-labelled exposure overlay are the only defensible gap. | **Verified core:** Sentinel-1 catalogue, WorldPop. Free CDSE account/token required to download Sentinel assets. | Disaster analyst selects locations for first verification after an event. | Pre/post radar swipe → preliminary inundation → population range. | **16** |
| 3 | **SolarChhat** | Waste & Energy | Low: PM Surya Ghar itself has Rooftop Visualisation; generic solar calculators are common. | **Verified core:** open buildings, NASA POWER, official scheme portal. Tariff/cost API is UNVERIFIED. | Household decides whether to begin official application based on a screening estimate. | Click building → area/irradiance scenario → subsidy cap → official hand-off. | **15** |
| 4 | **Dhuaan Alert** | Air | **Novelty weak:** AQEWS/DSS already provide 3-day Delhi forecasts and biomass-burning contribution; UrbanEmissions provides 72-hour forecasts. | FIRMS and wind forecast verified; historical official CPCB retrieval is not verified. | School/parent prepares an outdoor-activity alternative 1–2 days ahead, only after calibrated risk signal. | Nov-2024 replay: fire corridor and wind risk precede observed air deterioration. | **14** |
| 5 | **Parali Radar** | Air | Unproven: idea needs current, geocoded machine and plant availability, not just locations. | **UNVERIFIED critical layers:** public CRM-centre and biomass/CBG plant availability dataset/API. | Intended dispatch/booking decision requires a prohibited multi-party network. | Fire-to-nearest-facility map would be misleading without capacity data. | **8 — reject** |

## Recommendation

Build **ThandaShehar**, narrowed to a **Delhi summer heat-priority grid**. It is the best public-data-only project: no partner dependence, an understandable decision, visible environmental relevance, and a strong three-minute visual. October 8–11 is not peak Delhi heat season, so demo a cloud-free historical pre-monsoon scene and call it planning—not a live heat warning.

Do not build Parali Radar under the hard filter. Do not pitch Dhuaan Alert as a new AQI forecaster; AQEWS is materially more sophisticated. If built at all, it must be an explanatory, non-authoritative backtest tool.

---

# 1. Dhuaan Alert — Delhi smoke-arrival risk from FIRMS fires and wind

## User, decision, bounded impact

User: Delhi-NCR school administrator, parent, or facilities lead. Decision: 24–48 hours before a regional-smoke risk, decide whether to schedule an outdoor alternative or prepare indoor precautions. Output: an uncertainty-labelled *risk signal*, not health advice, causation, or an official AQI forecast.

Impact is realistic only as decision lead time. Delhi’s 2024 annual PM2.5 was reported at **104.7 µg/m³**, 2.6× the Indian annual standard (40 µg/m³) [D8]. No prototype can claim avoided exposure without a study.

## Existing solutions and novelty test

| Existing solution | What it does | Link | Gap / verdict |
|---|---|---|---|
| IITM/MoES **AQEWS** | Delhi 400 m, 3-day early-warning forecast; broader 10 km forecast up to 10 days; ingests near-real-time fire emissions. | [D1] | A simple fire/wind explainer could be easier to inspect, but it is not a better forecast. |
| IITM **DSS v1.0** | Estimates Delhi, surrounding-district, sector and Punjab/Haryana stubble-burning contribution; supports intervention analysis. | [D2] | **Novelty weak.** It already addresses the central claim. |
| **SAFAR** | IITM air-quality/weather observation and forecast service for metropolitan areas. | [D3] | No meaningful gap for an AQI dashboard. |
| **UrbanEmissions** | Next-72-hour Delhi criteria-pollutant and meteorology forecasts, around 1 km/hourly, plus source context. | [D4] | A transparent historical-proxy explainer is only a modest niche. |

## Exact data-access ledger

| Data source | Endpoint / sample request | Free / key / update / licence | Verification and use limit |
|---|---|---|---|
| NASA FIRMS VIIRS fires | `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/74,28,77,31/1` | Free **MAP_KEY** by email; FIRMS states 5,000 transactions/10 min. Near-real-time fire detections; cite FIRMS/NASA terms. | **Verified docs.** Key not created in this task. Detections are not confirmed crop-residue fires. [D5] |
| Forecast wind: Open-Meteo | `https://api.open-meteo.com/v1/forecast?latitude=30.9&longitude=75.8&hourly=wind_speed_10m,wind_direction_10m&forecast_days=3&timezone=Asia%2FKolkata` | No key for free non-commercial/open-source use; 7-day default/up to 16 days; CC BY 4.0 API licence/attribution. | **Verified HTTP 200.** Model forecast, not IMD and not a parcel trajectory. [D6] |
| ERA5 historical wind | AWS public dataset `s3://era5-pds/`; documented sample `https://era5-pds.s3.amazonaws.com/2008/01/data/air_temperature_at_2_metres.nc` | Public S3, monthly update, archive from 1979; Copernicus acknowledgement/licence. | **Verified registry/documentation.** Probe of assumed Nov-2024 wind key returned 403: exact object key is **UNVERIFIED** until listed with S3 tooling. [D7] |
| CPCB AQI via OGD | `https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69?api-key=579b464db66ec23bdd0000018a5a9c398fde4a705b986e0c5736c62e&format=json&limit=1` | OGD API key/demonstration key; catalogue says hourly and updated 25 Sep 2026; OGD/CPCB terms and attribution apply. | **Verified catalogue/syntax; direct request connection-refused in this environment.** Live API only; historical interface not verified. [D9] |
| CPCB CCR | `https://airquality.cpcb.gov.in/ccr` | Free UI, no public stable API verified. | **Verified UI. Do not scrape as an API.** [D10] |

## Required scientific validation check

**Trajectory plausibility: yes. Validation of the exact simple alert: no.** A 2026 peer-reviewed study combined VIIRS, AOD and HYSPLIT in 2020–24. Its 24–27 October 2024 trajectories reached Delhi from Punjab/Haryana in **36–48 h**; Delhi AOD rose from about **0.60 to 0.95**. It reports October–November fire counts explaining 78% of Delhi AOD variance, while noting other sources including Diwali [D11]. A 2024 Environmental Research study used PM2.5, satellite data, meteorology and 120-h HYSPLIT trajectories for 2019–22; its studied PM2.5 exceeded Indian 24-h standard by 6–9× [D12].

These validate transport relevance, not “fire count + 10 m wind predicts tomorrow’s PM2.5.” Boundary-layer height, inversion, humidity, dust, traffic and local emissions confound this. The MVP must publish hold-out precision/recall/calibration against a fixed alert threshold.

### Nov-2024 backtest availability

* FIRMS historic fires: available in principle through FIRMS archive/query with MAP_KEY [D5].
* ERA5 November 2024 winds: available in principle from the monthly archive, but exact retrieval key must be verified [D7].
* Official historic CPCB AQI/PM2.5: **UNVERIFIED**. The verified OGD resource is real-time. Do not claim a complete backtest until a legal timestamped observation archive is actually downloaded and frozen.

## Seasonality and scores

Peak post-paddy burning is late October/November. On Oct 8–11 feeds exist, but the dramatic event may not. Use a clearly labelled Nov-2024 replay.

| I | A | D | E | W |
|---:|---:|---:|---:|---:|
| 3 — preparation action is real but forecast duplicates exist | 4 — natural fit: scheduled Lambda/S3 snapshot of small feeds | 3 — proxy could be confused with official warning | 2 — official historical AQI access unresolved | 2 — map animation, but judges will ask about AQEWS |

**Natural AWS line:** Lambda + S3 can preserve versioned FIRMS/wind snapshots for a reproducible backtest.

---

# 2. Parali Radar — fires matched to CRM machinery and biomass/bio-CNG facilities

## User, decision, and hard-filter failure

Intended user: district agriculture/CRM officer deciding where to send machinery/outreach or straw. The CRM scheme gives 50% support to individual farmers and 80% to eligible groups establishing CHCs; official guidelines name `agrimachinery.nic.in` for programme data sharing [P1]. CEEW gives example CHC rental rates, e.g. Happy Seeder ₹1,400/acre with tractor/operator, balers/rakes ₹2,000/acre [P2].

However, a fire point plus straight-line distance cannot establish machinery availability, booking, residue amount/type, transport, plant intake capacity, or operator willingness. This is a multi-party operations/marketplace workflow—explicitly disallowed.

## Existing solutions and novelty

| Existing solution | What it does | Link | Verdict |
|---|---|---|---|
| CRM scheme / `agrimachinery.nic.in` | Subsidised CRM machinery and an intended online management/data-sharing system. | [P1] | No public current geocoded CHC availability API was found. This is a missing-data problem, not proof of novelty. |
| CEEW CHC research | Documents CHC services and price examples. | [P2] | Evidence, not a live dispatch inventory. |
| FIRMS | Exposes active-fire detections. | [D5] | Does not identify farmer need or actual facility availability. |

## Access ledger and seasonality

| Data source | Endpoint / terms | Status |
|---|---|---|
| FIRMS | Same area API as Dhuaan Alert; free MAP_KEY; NRT. | **Verified.** |
| CHC coordinates, machine inventory and availability | No stable nationwide public download/API verified. | **UNVERIFIED critical blocker.** |
| Biomass/bio-CNG coordinates, capacity and current acceptance | No complete, public, current geocoded endpoint verified. | **UNVERIFIED critical blocker.** |

Oct 8–11 is early for peak Punjab fire signal; a historical replay cannot repair the facility-data gap.

| I | A | D | E | W |
|---:|---:|---:|---:|---:|
| 3 — underlying problem real | 2 — no AWS dataset resolves missing facility state | 2 — “nearest” hides capacity and availability | 0 — requires prohibited network/manual curation | 1 — attractive but misleading |

**Hard-filter verdict: reject.**

---

# 3. SolarChhat — public footprint, irradiance, subsidy and payback screen

## User, decision, bounded impact

User: homeowner deciding whether to begin PM Surya Ghar’s official process. Show an explicit **screening scenario**, not a quote, engineering feasibility, roof safety certificate, net-metering approval, or binding payback. The official scheme targets one crore households; PIB reported more than 50.06 lakh installations by Aug 2026 [S1]. A demo reduces information friction; it does not prove additional adoption.

## Existing solutions and novelty

| Existing solution | What it does | Link | Verdict |
|---|---|---|---|
| PM Surya Ghar National Portal | Application, vendors, guidelines, progress and “Rooftop Visualisation”; site advertises potential-savings/free-home-visit flow. | [S2] | Direct core overlap; **novelty weak.** |
| Google Project Sunroof | Roof-specific production/savings using aerial imagery/3D shade/weather/incentives, published US-focused coverage. | [S3] | Strong precedent; do not imply equal 3D/shade accuracy from 2D polygons. |
| Overture/Microsoft footprints | Open building geometry, not verified solar feasibility/ownership. | [S4], [S5] | Enables transparent Indian screening, not accurate roof engineering. |

## Exact data-access ledger

| Data source | Endpoint / sample | Free / key / update / licence | Status and limitation |
|---|---|---|---|
| Overture buildings | `s3://overturemaps-us-west-2/release/2026-08-19.0/theme=buildings/type=building/*` | Free public cloud release; GeoParquet; release-specific Overture terms. | **Verified path.** Footprint ≠ usable roof / ownership. [S4] |
| Microsoft Global ML Building Footprints | `https://github.com/microsoft/GlobalMLBuildingFootprints` and linked `dataset-links.csv` | Free/no key; imagery 2014–24; CDLA-Permissive-2.0. | **Verified.** Not cadastral truth. [S5] |
| NASA POWER irradiance | `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=ALLSKY_SFC_SW_DWN&community=RE&longitude=77.2090&latitude=28.6139&start=20251001&end=20251003&format=JSON` | Free/no key; daily 1981–near-real-time; NASA attribution/terms. | **Verified HTTP 200.** Point irradiance is not roof-plane yield/shade. [S6] |
| PM Surya Ghar | `https://pmsuryaghar.gov.in/`; portal lists ₹30,000/kW first 2 kW + ₹18,000/kW to 3 kW; ₹78,000 cap above 3 kW. | Free UI; scheme info changes; no public developer API found. | **Verified UI, not API.** Link out; do not scrape. [S2] |
| Tariff/install cost/net metering | No national current public machine-readable source verified. | State/DISCOM-specific. | **UNVERIFIED.** Omit payback or show an editable fixed city scenario. |

## Seasonality and scores

Year-round data makes an October demo easy. It still cannot validate annual roof yield in October.

| I | A | D | E | W |
|---:|---:|---:|---:|---:|
| 3 — meaningful scheme but incumbents cover it | 4 — Athena can query AOI-filtered Overture GeoParquet | 4 — simple decision flow if assumptions visible | 3 — payback must be limited to a scenario | 1 — familiar product |

**Natural AWS line:** Athena queries only the selected AOI from Overture GeoParquet.

---

# 4. BaadhDrishti — Sentinel-1 flood extent and affected population

## User, decision, bounded impact

User: district disaster-control analyst. Decision: which population cells to verify first after an event. The tool shows a preliminary satellite-derived inundation candidate, acquisition dates, and an affected-population range—not water depth, trapped people, damage claims, or rescue dispatch.

## Existing solutions and novelty

| Existing solution | What it does | Link | Gap / verdict |
|---|---|---|---|
| Bhuvan Disaster Services | Government disaster/flood service. | [B2] | Flood visualisation itself is not novel. |
| Bhuvan National Hydrology Project Flood Geoportal | Flood hydrographs and inundation maps; forecast display June–October and inundation layers during events. | [B3] | Only defensible gap: reproducible source processing plus uncertainty/exposure overlay. |
| Open Sentinel-1/GEE workflows | Automated SAR change/threshold/DEM-mask workflows are public. | [B4] | Algorithm novelty low. |

## Exact data-access ledger

| Data source | Endpoint / sample | Free / key / update / licence | Status and limitation |
|---|---|---|---|
| Copernicus Sentinel-1 catalogue | STAC root `https://stac.dataspace.copernicus.eu/v1/`; POST `/search`: `{"collections":["SENTINEL-1"],"bbox":[87,21,88,22],"datetime":"2024-05-20/2024-06-10","limit":10}` | Search may be anonymous; bytes need free CDSE registration/OIDC bearer token; Copernicus terms. | **Verified STAC root HTTP 200/docs.** [B1], [B6] |
| AWS Sentinel-1 | Registry `https://registry.opendata.aws/sentinel-1/`, described requester-pays in eu-central-1. | AWS credentials/requester-pays cost. | **Verified access limitation.** Do not use as no-account critical path. [B7] |
| WorldPop | `https://api.worldpop.org/v1/services`; constrained 100 m data `https://hub.worldpop.org/geodata/listing?id=100` | Free/no key stated; release/modelled data; CC BY 4.0. | **Verified.** Residence distribution, not live presence. [B8] |
| Bhuvan flood map | `https://bhuvan.nrsc.gov.in/nhp/webgis-flood/map` | Free UI; no documented stable programmatic service verified. | **Verified UI only; do not scrape.** [B3] |
| DEM/permanent water exclusion | Not fully verified this round. | — | **UNVERIFIED optional layer.** |

## Seasonality and scores

Flood/cyclone is possible in October but not guaranteed. Sentinel acquisition timing also cannot be guaranteed; use a historical Indian replay. Sentinel-1 is not continuous: a cited assessment discusses 12-day single-satellite revisit constraints [B9].

| I | A | D | E | W |
|---:|---:|---:|---:|---:|
| 4 — clear first-review decision | 4 — SageMaker geospatial/ECS batch naturally fits raster work | 3 — uncertainty must be prominent | 3 — SAR processing/token/scene cadence are substantial | 2 — strong swipe, common technique |

**Natural AWS line:** a SageMaker geospatial or ECS batch job performs raster differencing; S3 serves versioned derived tiles.

---

# 5. ThandaShehar — Landsat surface-temperature × population priority grid

## User, decision, bounded impact

User: Delhi ward/heat-action-plan NGO or planner. Decision: choose the first five cells for shade, cooling-access, or heat-outreach inspection before summer. Rank cells by a transparent `positive LST anomaly × resident population` screening score. Landsat LST is **surface skin temperature, not air temperature or personal heat risk**.

Delhi/NCR Landsat research finds urban-heat-island expansion and reports built-up/impervious expansion matching temperature hotspots [T1]. This motivates targeting—not a claim that the product predicts illness.

## Existing solutions and novelty

| Existing solution | What it does | Link | Verdict |
|---|---|---|---|
| Delhi heat-action planning | Response/preparedness framework, not verified here as a public ward-LST queue. | Prior report DDMA reference. | Complement, not replacement. |
| Delhi/NCR Landsat UHI research | Academic mapping of surface temperature/land cover. | [T1], [T2] | Method is not new. |
| USGS LST product | Analysis-ready global LST, explicitly useful for UHI. | [T3] | Data exists; modest gap is a transparent decision queue. |

**Novelty verdict: moderate, not high.** Do not say “first heat map.”

## Exact data-access ledger

| Data source | Endpoint / sample | Free / key / update / licence | Status and limitation |
|---|---|---|---|
| Landsat ST discovery | STAC root `https://landsatlook.usgs.gov/stac-server`; example `https://landsatlook.usgs.gov/stac-server/search?collections=landsat-c2l2-sr&bbox=76.8,28.4,77.4,29.0&datetime=2026-04-01/2026-06-30&limit=10` | Metadata search free/no key documented. L2 ST generally 24–72 h after processing. | **Endpoint/docs verified; sample GET returned HTTP 400, so implement POST/STAC client.** [T3], [T4] |
| Landsat assets | `s3://usgs-landsat/collection02/level-2/` | Open but requester-pays; AWS credentials + `--request-payer requester`; USGS terms/attribution. | **Verified.** Avoid direct S3 asset dependency for no-account demo. [T5] |
| ST conversion | `Kelvin = DN * 0.00341802 + 149.0`; use ST and QA/cloud bands. | Per-scene. | **Verified.** [T4] |
| WorldPop | Same endpoint/license as BaadhDrishti. | Free; CC BY 4.0; 100m modelled annual data. | **Verified.** [B8] |
| Delhi ward geometry | Prefer authoritative official source if verified; otherwise 500m/H3 grid. | — | **Official downloadable ward endpoint UNVERIFIED.** Use grid, not questionable boundaries. |

## Seasonality and scores

October is not peak Delhi heat season. Use a source-labelled historical cloud-free May scene; position as planning for the coming summer.

| I | A | D | E | W |
|---:|---:|---:|---:|---:|
| 4 — converts thermal inequality into a specific inspection queue | 4 — raster batch + S3 tiles is a natural fit | 4 — “hot surface + people” is legible | 3 — QA/cloud/grid work is real; not live heat warning | 3 — visually clear thermal ranking |

**Natural AWS line:** SageMaker geospatial or an ECS batch job processes the raster, and S3/CloudFront serves versioned map tiles.

---

# Three-day ThandaShehar scope

Day 1: freeze one Delhi AOI and a 500m/H3 grid; discover 2–3 cloud-filtered Landsat scenes via STAC; select a historical May scene; apply USGS ST scale and QA; overlay WorldPop.

Day 2: calculate robust LST anomaly and `population × positive anomaly`; provide exactly three human-review prompts: inspect shade, heat outreach, review cooling access.

Day 3: add provenance drawer (scene ID/date, QA coverage, WorldPop year, formula); record historical-scene → ranked-cells → action-card flow; add “not a heat forecast, population count, or emergency-dispatch tool.”

---

# Sources

[R1] Bharat Builds Tour Environmental Hacks, local `README.md`, lines 87–110 and 127–133.

[D1] IITM/MoES, *AQEWS 2024.* https://www.tropmet.res.in/~MOES/IITM-Exhibits-2023-C17/Exhibit/AQEWS_2024.pdf
[D2] Jena, C. et al. (2024), “DSS v1.0 for air quality management in Delhi.” *GMD* 17, 2617–2640. https://doi.org/10.5194/gmd-17-2617-2024
[D3] IITM SAFAR. https://safar.tropmet.res.in/
[D4] UrbanEmissions Delhi forecasts. https://urbanemissions.info/delhi-air-quality-forecasts
[D5] NASA FIRMS API/MAP_KEY docs. https://firms.modaps.eosdis.nasa.gov/api/ ; https://firms.modaps.eosdis.nasa.gov/api/map_key/
[D6] Open-Meteo forecast API. https://open-meteo.com/en/docs ; https://open-meteo.com/docs/openapi/forecast.yml
[D7] AWS Registry ERA5; Planet OS access notes. https://registry.opendata.aws/ecmwf-era5/ ; https://github.com/planet-os/notebooks/blob/master/aws/era5-pds.md
[D8] CSE Delhi annual PM2.5 analysis. https://cseindia.org/content/downloadreports/12563
[D9] OGD/CPCB real-time AQI. https://www.data.gov.in/resource/real-time-air-quality-index-various-locations
[D10] CPCB CCR. https://airquality.cpcb.gov.in/ccr
[D11] “Tracing the haze…” (2026), PMCID PMC12823738. https://pmc.ncbi.nlm.nih.gov/articles/PMC12823738/
[D12] “Aerosol-PM2.5 Dynamics…” (2024), *Environmental Research*, 119141. https://doi.org/10.1016/j.envres.2024.119141
[P1] Crop Residue Management Guidelines 2023–24. https://gobardhan.sbm.gov.in/assets/guidelines/Crop_Residue_Management_Guidelines_2023-24.pdf
[P2] CEEW CHC research. https://www.ceew.in/publications/improving-access-to-crop-residue-management-solutions-with-custom-hiring-centres-in-agriculture
[S1] PIB, 4 Aug 2026, PM Surya Ghar milestone. https://www.pib.gov.in/PressReleasePage.aspx?PRID=2294208&reg=48&lang=1
[S2] PM Surya Ghar portal. https://pmsuryaghar.gov.in/ ; https://partner.pmsuryaghar.gov.in/
[S3] UNFCCC Project Sunroof. https://unfccc.int/climate-action/momentum-for-change/ict-solutions/project-sunroof
[S4] Overture Buildings guide. https://docs.overturemaps.org/guides/buildings
[S5] Microsoft Global ML Building Footprints. https://github.com/microsoft/GlobalMLBuildingFootprints
[S6] NASA POWER Daily API. https://power.larc.nasa.gov/docs/services/api/temporal/daily/
[B1] CDSE Sentinel-1. https://dataspace.copernicus.eu/data-collections/sentinel-data/sentinel-1
[B2] Bhuvan flood service. https://bhuvan-app1.nrsc.gov.in/disaster/disaster.php?id=flood
[B3] Bhuvan NHP Flood Geoportal. https://bhuvan.nrsc.gov.in/nhp/webgis-flood/map
[B4] Sentinel-1 flood mapping GEE code. https://github.com/kashif061/sentinel1-flood-mapping-gee
[B5] Near-real-time flood mapping from Sentinel data (2026). https://isprs-archives.copernicus.org/articles/XLIX-B3-2026/797/2026/isprs-archives-XLIX-B3-2026-797-2026.pdf
[B6] CDSE STAC documentation. https://documentation.dataspace.copernicus.eu/APIs/STAC.html
[B7] AWS public-data access matrix. https://cogeotiff.github.io/rio-tiler-pds
[B8] WorldPop services and constrained population data. https://api.worldpop.org/v1/services ; https://hub.worldpop.org/geodata/listing?id=100
[B9] Tarpanelli et al., Sentinel flood-detection assessment. https://nhess.copernicus.org/preprints/nhess-2022-63/nhess-2022-63-manuscript-version5.pdf
[T1] Ghosh et al. (2018), Delhi/NCR Landsat UHI. https://isprs-annals.copernicus.org/articles/IV-5/71/2018/isprs-annals-IV-5-71-2018.pdf
[T2] Kapuganti et al. (2025), Delhi LST/UHI. https://doi.org/10.1007/s10661-025-14390-y
[T3] USGS Landsat C2 surface temperature. https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature
[T4] USGS Landsat C2 Level-2 products. https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products
[T5] Landsat STAC and requester-pays access notes. https://landsatlook.usgs.gov/stac-server/api.html ; https://github.com/opendatacube/datacube-dataset-config/blob/main/usgs-landsat-collection2.md

## Research limitations

1. Representative endpoints were tested; every STAC collection ID, scene asset and raster QA convention still needs a code-level check before demo.
2. Search retrieval was intermittent; competitor scan is grounded, not exhaustive.
3. “No public API verified” does not mean no database exists. It means the team must not promise it during the hackathon.
4. Fires are detections, LST is not air temperature, footprints are not roof feasibility, population grids are modelled residences, and SAR flood masks have false positives/negatives.
5. Any historical replay must visibly show its date and never be passed off as live data.
