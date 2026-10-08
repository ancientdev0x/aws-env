# Bharat Builds Tour — Environmental Hacks Research Brief

Research date: 8 October 2026  
Scope: India-first concepts that have a credible 3–4 day MVP path. The emphasis is not another generic dashboard: every proposal starts with an operational decision a resident, school, civic worker, recycler, or facility manager can make.

## Executive shortlist

| Rank | Concept | Track | Core user | 3–4 day feasibility | Why it is differentiated |
|---|---|---|---|---|---|
| 1 | **JalSetu**: water-loss, tanker and recharge decision layer | Heat & Water | Bengaluru apartment / ward | High (5/5) | Connects scarcity, leakage, tanker reliability, rain and groundwater rather than treating them as separate problems. |
| 2 | **SaansSafe Schools**: exposure-aware school-day planner | Air | Delhi-NCR school staff and parents | High (5/5) | Converts city AQI into child-specific, route- and classroom-level actions with an auditable protocol. |
| 3 | **HeatShift**: worker heat-risk routing and check-in | Heat & Water | delivery, construction and sanitation supervisors | High (5/5) | Plans shifts and cooling/water stops, not just heat alerts. |
| 4 | **ReLoop**: traceable e-waste handoff network | Waste & Energy | households, informal collectors, authorised recyclers | High (4/5) | Gives informal collectors a paid, safe bridge to formal processing without pretending to replace their network. |
| 5 | **Drain2Recharge**: crowdsourced flood-to-recharge map | Heat & Water | ward engineers and commuters | Medium-high (4/5) | Uses waterlogging reports as evidence for drain blockage and recharge opportunity. |
| 6 | **BinProof**: contamination feedback for bulk waste generators | Waste & Energy | apartments, campuses, canteens | High (5/5) | A low-cost photo + weight workflow that produces evidence and behaviour nudges before collection. |
| 7 | **SolarShare / EVFlex**: demand-aware clean-energy nudges | Waste & Energy | housing societies / EV fleets | Medium-high (4/5) | Forecasts useful actions around rooftop generation instead of making a static solar calculator. |
| 8 | **Airshed Signal**: explainable smoke-and-exposure incident board | Air | Delhi-NCR residents, researchers, local officials | Medium (3/5) | Links monitor readings with satellite fire signals and wind direction while explicitly reporting uncertainty. |

## Evidence and design principles

1. **Do not overclaim hyper-local precision.** Regulatory monitors are sparse relative to neighbourhood variation. Low-cost sensors, satellite products, and crowd reports are valuable as *screening signals*, but their calibration, timestamp, and source must stay visible. For health decisions, show an action tier and confidence rather than a false exact concentration.
2. **Airshed, not city-only, logic is essential for Delhi.** A WRF-Chem study found Delhi-NCR-only crop-residue controls reduced NCT Delhi PM2.5 only 2–3%, versus about 10% when extended across the full airshed; combined airshed-wide measures were materially stronger [A2]. A product must therefore distinguish local exposure actions from claims of local causation.
3. **Bengaluru’s flood and drought are the same systems problem.** Research using 1997–2023 data describes rising impervious cover, lake/drain disruption and groundwater depletion together [W4]. A winning solution should retain the location, severity, and outcome of each monsoon incident so the same data can guide dry-season recharge action.
4. **Design with informal workers rather than routing around them.** NITI Aayog reports that informal activity accounts for about 62% of India’s e-waste processing, while only 2,808 collection centres serve the population [E1]. A marketplace that demands workers become formal overnight will fail; a tool should improve proof of collection, safety referrals, and batch aggregation.

---

# 1. Air

## A1. SaansSafe Schools — child exposure and school-day action planner

**Problem statement and geography.** Delhi-NCR schools need defensible, rapid decisions on outdoor sport, bus waiting, classroom ventilation/filtration and parent alerts during severe PM episodes. Citywide AQI alone is not a child’s exposure: it omits the route, time outdoors, indoor condition, and whether a child has asthma. Target pilot: 3–10 schools around Delhi-NCR monitors, then low-resource schools that lack an EHS team.

**Why this is critical.** Delhi recorded 24-hour PM2.5 of 182 and 171 µg/m³ in the January 2025 high-pollution survey days; those days were “Very Poor” under India’s NAQI. The survey found significantly greater symptoms and disruptions, with adjusted odds roughly 3.8–4.8 for several impacts and needs for assistance [A3]. A 2025 Delhi trend analysis reports average November 2024 AQI of 374 and cites 5,798 school closures affecting an estimated 4.41 million children in an earlier episode [A1]. These values support a preparedness product, not a diagnostic medical claim.

**MVP workflow.**
- Ingest CPCB / Sameer AQI and a selected station or device reading; allow school staff to enter classroom CO2 / PM2.5 from a low-cost sensor if available.
- Create a daily action card: `normal`, `reduce outdoor exertion`, `move activity indoors`, `high-risk child protocol`; list why the tier triggered, data freshness, and confidence.
- Let staff log mitigation actions and symptoms anonymously in aggregate; compare before/after across days without storing health records or names.
- Provide safe route/time suggestions based on exposure score (AQI × expected outdoor minutes × route proximity proxy), clearly labelled as estimated.

**AWS architecture.** A SAM CLI monorepo defines API Gateway + Lambda endpoints. EventBridge runs ingestion every hour; raw API and sensor payloads go to S3 (partitioned by date/station), validated events to DynamoDB, and time/location searches to OpenSearch. A Lambda calculates policy tiers from configurable thresholds stored in DynamoDB. Cognito protects school workspaces; Cedar policies enforce that a parent sees only their school’s public guidance, while a staff member can submit a class-level log. LocalStack supplies local S3/DynamoDB/EventBridge/Lambda-compatible development. Use SageMaker only as an optional later calibration/forecast experiment; it is not required for the demo.

**Demo data and sources.** CPCB’s National AQI / Sameer data is the live reference [D1]. Seed with the cited Jan 2025 episode and synthetic, clearly marked classroom readings. Show NASA FIRMS only as regional context, not proof of an individual school’s smoke source [D2].

**Hackathon feasibility: 5/5.** Build the action engine, school dashboard, audit trail, and a two-station demo. Do not attempt clinical advice, personal health prediction, or hardware manufacture.

## A2. Airshed Signal — explainable Delhi smoke/exposure incident board

**Problem statement and geography.** Residents and civic groups see a severe AQI number but cannot tell whether to act locally (dust, traffic, indoor exposure) or treat it as a regional episode. Target: Delhi-NCR during post-monsoon, with an expandable Punjab/Haryana fire context map.

**Why this is critical.** Satellite/trajectory research for 2020–2024 found extreme-fire-day parcels reaching Delhi from Punjab–Haryana within 36–48 hours, accompanied by Delhi AOD increase from approximately 0.60 to 0.95 in late Oct/early Nov 2024 [A4]. But source attribution remains mixed: a review notes local traffic, residential biomass and construction alongside regional inflow [A4]. The tool must say “consistent with” rather than “caused by.”

**MVP workflow.** Combine hourly AQI, NASA FIRMS VIIRS 375 m active fires, wind direction/speed, and voluntary photo reports. A rules-based explanation panel ranks evidence: monitor rise, upwind fire density, wind alignment, local construction report count. It emits a confidence-labelled incident note and practical exposure actions; it does not allocate legal blame.

**AWS architecture.** EventBridge collectors → S3 raw lake → Lambda normalizer → OpenSearch geospatial/time indexes. A Step Functions workflow produces a reproducible incident snapshot. DynamoDB holds report moderation state; SQS buffers photo analysis; Rekognition custom labels is explicitly out of scope for the MVP—use human moderation or metadata-only reports. Cedar controls moderator/admin actions. Deploy using SAM; integration tests run against LocalStack.

**Hackathon feasibility: 3/5.** Credible if restricted to a historical replay plus 1–2 live feeds. Avoid an unvalidated ML source-apportionment model.

---

# 2. Heat & Water

## H1. JalSetu — apartment/ward water-loss, tanker and recharge decision layer

**Problem statement and geography.** Peripheral Bengaluru housing societies face a compound operational problem: uncertain borewell yield, variable tanker availability/prices, hidden internal leaks, and monsoon runoff that could recharge groundwater. Target pilot: Whitefield/KR Puram/Yelahanka-type periphery, with a society manager and residents as separate roles.

**Why this is critical.** In the 2024 pre-monsoon crisis, estimated city demand was 1,891 MLD versus 1,273 MLD current supply, a 618 MLD deficit [W1]. Reported groundwater extraction increased from 4,580.3 to 4,626.7 ha.m from 2022 to 2023 while the extraction stage rose from 192.62% to 217%; the city was categorised over-exploited [W1]. Independent reporting of the Urban Water Balance estimated about 448 MLD (nearly 30%) lost from Bengaluru’s 1,520 MLD system, including estimated real losses of 331 MLD [W2]. Residents themselves report building/using tanker directories and recurrent water-availability concerns [C1, C2].

**MVP workflow.**
- Society manager records daily meter/borewell/tanker volume, price, expected demand and rainwater-harvesting capacity.
- A mass-balance rule flags unexplained use and probable leakage (not a confirmed leak), gives a “days of buffer” estimate, and calculates a transparent tanker cost range from local submissions.
- A rain-event checklist prioritises first-flush, filtration, recharge-pit inspection, and a post-monsoon evidence log.
- Ward view anonymises society data into “shortage / excess runoff / suspected loss” cells; no household consumption is public.

**AWS architecture.** Mobile/PWA → API Gateway → Lambda; DynamoDB stores daily entries and consent flags; S3 stores meter-photo evidence; EventBridge schedules rainfall and alert jobs; OpenSearch powers ward and time queries. Amazon Forecast is unnecessary: a deterministic rolling average is more credible in four days. Cedar separates resident, society manager, tanker provider, and ward analyst permissions. LocalStack supports demo-local deployment; CloudWatch metrics capture ingestion failures.

**Demo data and sources.** Seed with disclosed volumes above, synthetic society meters marked `DEMO`, IMD forecast/observations where licensing permits, and OpenStreetMap building/road context [D3].

**Hackathon feasibility: 5/5.** Start with one society; demonstrate a leak alert, a tanker comparison, and a rain-recharge checklist. Do not promise verified tanker quality or groundwater potability.

## H2. Drain2Recharge — flood reports that become maintenance and recharge evidence

**Problem statement and geography.** A commuter can report a flooded road but the report rarely becomes an actionable, deduplicated work item or a dry-season recharge design input. Target: Bengaluru ward corridors; readily adapted to Mumbai/Delhi monsoon wards.

**Why this is critical.** Bengaluru reporting cites monsoon runoff near 982 MLD, 73% above dry-season runoff (568 MLD), and severed lake links that turn overflow into flooding [W2]. The same source describes about 45% of rainfall as runoff, while wastewater-filled lakes lack buffering capacity [W2]. A peer-reviewed 2025 study reports built-up area growing from 42% to 86% across two decades and 70% encroachment of historical lakes [W4]. Reddit reports show residents already map/announce waterlogged locations and route avoidance, a signal that the usability gap is real [C3].

**MVP workflow.** A citizen submits location, depth category, passability, photo, and timestamp. Nearby reports cluster into an incident; a public map offers route avoidance, while a verified ward queue adds “clear drain / inspect culvert / assess recharge feasibility.” After rain, the system sends a closure/outcome request so reports become labelled data, not a complaint wall.

**AWS architecture.** API Gateway/Lambda accepts reports; S3 keeps photo originals; DynamoDB + geohash supports nearest incident lookup; OpenSearch supports map/filter queries; EventBridge sends status reminders; SQS isolates image-processing jobs. A Lambda image pipeline removes EXIF metadata and generates thumbnails. Cedar ensures only authorised ward staff can reveal reporter contact details. Use SAM/LocalStack for local repeatability.

**Hackathon feasibility: 4/5.** Deliver reliable reporting, clustering, queueing, and a simulated rain-event replay. Do not claim hydrological modelling or municipal integration without agency data.

## H3. HeatShift — heat-risk work planner for outdoor workers

**Problem statement and geography.** Outdoor workers must decide *when and where* to work, rest, drink and check in. General heat alerts do not translate into supervisor schedules, and they often miss shade, travel time, workload and individual vulnerability. Target: delivery fleet captains, construction supervisors, municipal sanitation teams; pilot story in Ahmedabad.

**Why this is critical.** Ahmedabad’s May 2010 heatwave reached nearly 47°C and was associated with 1,334 additional deaths in May (43% above baseline mortality) [H1]. Ahmedabad’s Heat Action Plan was first implemented in 2013; the World Bank case study estimates 2,380 deaths avoided in 2014–15 [H1]. The model’s success validates alert-to-action coordination, but it also exposes a product gap: local work plans and compliance evidence are still operationally hard.

**MVP workflow.** Ingest IMD forecast; let a supervisor define shift windows, tasks, workers and known shade/water points. Generate a heat-work plan with alert tier, rest/water reminders, one-tap check-ins, and missed-check-in escalation. Display “forecast, not medical clearance.” Default to group-level analytics; do not collect diagnoses.

**AWS architecture.** EventBridge imports forecast on a schedule; Lambda scores task-time combinations; DynamoDB stores shifts/check-ins; SNS sends opt-in SMS/push; OpenSearch gives supervisors a timeline; S3 retains exported safety plans. Cognito/Cedar implements worker/supervisor/organisation roles. SAM + LocalStack enables the offline demo stack.

**Hackathon feasibility: 5/5.** The MVP is scheduling plus check-ins, demonstrated with Ahmedabad forecast replay and HAP action thresholds; no wearable device or proprietary HR system integration needed.

---

# 3. Waste & Energy

## E1. ReLoop — chain-of-custody for e-waste handoffs and safe aggregation

**Problem statement and geography.** Households want convenient disposal; informal collectors have collection reach but few benefits from a traceable route to authorised processing; formal recyclers lack predictable feedstock. Target: Delhi-NCR or Bengaluru phone/laptop collection cluster and one partnering authorised recycler.

**Why this is critical.** NITI Aayog’s 2026 report says informal processing remains about 62%, only 2,808 collection centres serve India, and formal recycling capacity is about 1.75 MMT across 400+ authorised recyclers/dismantlers [E1]. Earlier peer-reviewed field research found formal facilities constrained by few collection centres and competition for feedstock; it estimates 95% informal recycling in the study context [E2]. This is an inclusion and worker-safety problem—not merely a consumer reminder problem.

**MVP workflow.** Generate a QR handoff receipt with category, condition, approximate weight, collection neighbourhood, price/fee, and each custodian. Aggregate batches until an authorised recycler accepts pickup. Give collectors a non-public earnings/batch history and safety/PPE referral checklist. The consumer sees a disposition status, not a brittle “100% recycled” claim unless the downstream facility attests it.

**AWS architecture.** QR-capable PWA → Lambda/API Gateway → DynamoDB chain-of-custody records. S3 stores receipts/photos; EventBridge triggers pickup reminders; SNS sends status notifications; OpenSearch supports authorised recycler and category search. Cedar is central: collector sees their jobs; recycler sees offered batches; a consumer sees only their own serialised handoff. LocalStack makes the receipt workflow demoable without cloud credentials.

**Hackathon feasibility: 4/5.** Ship the QR flow, mock authorised-recycler acceptance, and transparency dashboard. Do not tokenize waste, handle hazardous-material routing, or represent yourself as a licensed recycler.

## E2. BinProof — source-segregation feedback for apartments and bulk generators

**Problem statement and geography.** Mixed/contaminated waste destroys recovery value before it reaches processing. Bulk waste generators need simple evidence of which building/floor/event is causing contamination and whether a nudge works. Target: Bengaluru apartment, hostel, office or cafeteria.

**Why this is critical.** India’s CPCB Solid Waste Management portal now specifies mandatory four-stream source segregation (wet, dry, sanitary, special care) and identifies bulk generators at thresholds including ≥100 kg/day of solid waste [E3]. Bengaluru’s OpenCity catalogue exposes BBMP waste-processing plants, dry-waste centres, landfill locations and segregated collection data [E4]. The product gap is immediate feedback at the point of collection, before a mixed bin leaves the campus.

**MVP workflow.** Collector weighs labelled wet/dry bins, records a contamination grade and optionally captures a photo. Residents see weekly building-level scores, “top contamination type,” and a specific micro-nudge. Facility staff can export a collector handoff report. Start with staff-entered labels; optionally add a lightweight image classifier later, and never let a model impose fines without review.

**AWS architecture.** API Gateway/Lambda ingests weigh-ins; DynamoDB stores bin events; S3 stores photos; OpenSearch powers trends; EventBridge calculates weekly scorecards. A SageMaker endpoint is optional and should only assist category suggestions with confidence shown; it is out of the critical demo path. Cedar protects staff/collector/admin actions. SAM tests run against LocalStack.

**Hackathon feasibility: 5/5.** Build manual workflow, leaderboard, photos, and export. Demonstrate with synthetic bins and a clear human-review flow.

## E3. SolarShare / EVFlex — rooftop solar and EV charging action nudges

**Problem statement and geography.** Housing societies and small commercial sites have rooftop solar/EV charging decisions but lack a simple way to shift flexible loads into generation windows, detect abnormal self-consumption, or coordinate chargers fairly. Target: one Bengaluru apartment/office with a solar inverter feed or CSV export.

**Why this is critical.** This is a viable climate/energy optimisation angle but should be pitched as a *decision support MVP*, not a claim that it can independently optimise the grid. The strongest related waste/energy evidence in this brief is the need for data-backed operational flows; CPCB’s open SWM portal and OGD waste dataset demonstrate that government data is increasingly available, but solar/EV telemetry will usually come from the site [E3, D4].

**MVP workflow.** Import inverter/charger CSV (or simulator), forecast next-day generation with a transparent baseline, propose non-critical charging/laundry/pump windows, and show acceptance and estimated kWh shifted. Users set a hard “must be charged by” constraint. Avoid remote control in the hackathon; generate approval-required recommendations.

**AWS architecture.** S3 CSV upload triggers Lambda validation; DynamoDB holds devices and preferences; EventBridge executes scheduled recommendation jobs; OpenSearch renders timelines; SES/SNS sends nudges. Use Cedar for household vs facility-manager access. SAM/LocalStack supports the demo. A later option is SageMaker for forecast comparison, but baseline forecasting is enough.

**Hackathon feasibility: 4/5.** Demonstrate with generated but explicitly labelled load/solar data, one upload flow and recommendation explanation. Do not claim utility integration or savings without metered verification.

---

# Suggested build plan and judging narrative

## Recommended primary build: JalSetu

**One-sentence pitch:** “JalSetu turns a housing society’s scattered tankers, borewell readings, leaks and rain into one transparent water-resilience operating board.”

**Day 1:** scaffold SAM/LocalStack; create roles and core tables; build data-entry PWA; seed an explicitly synthetic Bengaluru society.

**Day 2:** add buffer/leak heuristics, tanker comparison, rain/recharge checklist and action log; make every alert explain its inputs.

**Day 3:** build ward anonymisation, dashboard, CSV export and test suite; record a 90-second incident demo: abnormal use → suspected leak → action → buffer restored.

**Day 4:** polish data provenance, consent screens, architecture diagram, deployment instructions, failure states and pitch. Stress that leakage is a *screening alert*, tanker rates are *user-reported*, and water quality needs laboratory/utility verification.

## Evaluation criteria for any concept

- **Impact:** Does it reduce exposure, water loss, unsafe handling or avoidable emissions in a measurable operational loop?
- **Evidence:** Are source links, timestamps, data freshness, uncertainty and synthetic-vs-live labels visible?
- **Adoption:** Can the first user finish an action in under two minutes without buying hardware?
- **Equity:** Does the product avoid excluding informal workers, low-connectivity users and schools/societies with fewer resources?
- **Technical credibility:** Is the critical path serverless, event-driven, observable and locally reproducible with SAM + LocalStack? Is ML optional unless validated?

---

# Sources, datasets, and community signals

## Air

- **[A1]** Islam, A. & Islam, F. (2025). *Decadal Analysis of Delhi’s Air Pollution Crisis: Unraveling the Contributors.* arXiv:2506.24087. https://arxiv.org/html/2506.24087v1
- **[A2]** *Delhi cannot clean its air alone: airshed-scale mitigation outperforms local controls even under unfavourable winter meteorology* (2026). Nature/npj Climate and Atmospheric Science. https://www.nature.com/articles/s44407-026-00065-6
- **[A3]** *Real-time impacts of air pollution on the health, well-being, and daily life of children and young people in Delhi and Dhaka* (2025 preprint). https://medrxiv.org/content/10.1101/2025.10.14.25338037v1.full-text
- **[A4]** *Tracing the haze: satellite-based assessment of stubble burning and air quality in Delhi* (2026). PMC. https://pmc.ncbi.nlm.nih.gov/articles/PMC12823738/
- **[D1]** Central Pollution Control Board, National AQI/Sameer. https://app.cpcbccr.com/AQI_India/
- **[D2]** NASA FIRMS, VIIRS active-fire data. https://firms.modaps.eosdis.nasa.gov/

## Heat & Water

- **[W1]** *Study on the Water Scarcity Crisis in Bengaluru City, India during Pre-Monsoon 2024—Causes and Sustainable Solutions.* Journal of Civil & Environmental Engineering. https://www.omicsonline.org/open-access/study-on-the-water-scarcity-crisis-in-bengaluru-city-india-during-premonsoon-2024causes-and-sustainable-solutions-2157-7617-1000884-138431.html
- **[W2]** Newslaundry / WELL Labs reporting (2024), *Over-exploited groundwater, neglected lakes: why Bengaluru is facing a water crisis.* https://newslaundry.com/2024/09/10/2024/04/08/2024/03/20/over-exploited-groundwater-neglected-lakes-heres-why-bengaluru-is-facing-a-water-crisis
- **[W3]** WELL Labs, *Bengaluru Urban Water Balance Report* (linked in W2). https://welllabs.org/wp-content/uploads/2023/10/WELL-Labs_Bengaluru-Urban-Water-Balance-Report.pdf
- **[W4]** *From Crisis to Resilience: Rethinking Urban Flooding and Groundwater Recharge in Bengaluru City, India* (2025). Water and Environment Journal. https://onlinelibrary.wiley.com/doi/full/10.1002/wwp2.70098
- **[H1]** World Bank (2024), *Saving Lives Through a Heat-Health Action Plan: India.* https://documents1.worldbank.org/curated/en/099826201272616643/pdf/IDU-ae8ad29c-bee3-4241-a9a3-09de535467c3.pdf
- **[H2]** Azhar, G. S. et al. (2014), *Heat-related mortality in India: Excess all-cause mortality associated with the 2010 Ahmedabad heat wave.* International Journal of Public Health. https://doi.org/10.1007/s00038-014-0563-4
- **[H3]** Ahmedabad Municipal Corporation / IIPHG (2018), *Ahmedabad Heat Action Plan.* https://iiphg.edu.in/images/pdfs/NRDC/HAP_2018_English.pdf
- **[D3]** India Meteorological Department, weather and heat-wave warnings. https://mausam.imd.gov.in/

## Waste & Energy

- **[E1]** NITI Aayog (2026), *Advancing Circular Economy of Waste Electronic and Electrical Equipment (E-waste) and Lithium-Ion Batteries in India.* https://niti.gov.in/sites/default/files/2026-01/Advancing-Circular-Economy-of-Waste-Electronic-and-Electrical-Equipment-Ewaste-and-Lithium-Ion-Batteries-in-India.pdf
- **[E2]** Dutta, D. & Goel, S. (2021), *Understanding the gap between formal and informal e-waste recycling facilities in India.* Waste Management, 125, 163–171. https://doi.org/10.1016/j.wasman.2021.02.045
- **[E3]** Central Pollution Control Board, Centralised Online Portal for Solid Waste Management / SWM Rules 2026. https://swm.cpcb.gov.in/
- **[E4]** OpenCity, *BBMP Solid Waste Management Data.* https://data.opencity.in/dataset/bbmp-solid-waste-management-data
- **[D4]** Open Government Data Platform India, state/UT-wise solid-waste details from CPCB annual report (2020–21). https://www.data.gov.in/resource/stateut-wise-details-solid-waste-management-central-pollution-control-board-cpcb-annual

## Community signals (problem discovery, not empirical prevalence estimates)

- **[C1]** r/bangalore, *I built a simple site to help Bangalore residents find reliable [water tankers]* (2025). https://www.reddit.com/r/bangalore/comments/1rx10ws/i_built_a_simple_site_to_help_bangalore_residents/
- **[C2]** r/indianrealestate, *Is Bengaluru’s next water crisis already starting?* (2026). https://www.reddit.com/r/indianrealestate/comments/1vdn5jl/is_bengalurus_next_water_crisis_already_starting/
- **[C3]** r/bangalore, *Bengaluru Water Log — Mapping where water flows & drains* (2025). https://www.reddit.com/r/bangalore/comments/1kq7ke4/bengaluru_water_log_mapping_where_water_flows/

## AWS/open-source implementation references

- AWS SAM CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html
- LocalStack: https://docs.localstack.cloud/
- Amazon OpenSearch Service: https://docs.aws.amazon.com/opensearch-service/
- Cedar policy language: https://docs.cedarpolicy.com/
- AWS Well-Architected Serverless Lens: https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/

## Research limitations

- Web and published sources vary in date, methodology and jurisdiction. Quantitative values above remain tied to their cited source rather than being treated as universally current facts.
- Reddit/community threads establish lived friction and adoption hypotheses; they do not establish incidence or causal effects.
- Satellite fire, AOD and wind evidence can support regional context but cannot prove a specific local emitter caused a particular monitor spike.
- No proposal substitutes for public-health, utility, municipal, recycling, or hydrological professional decisions. Consent, minimisation of location/health data, retention limits and accessible non-app channels are MVP requirements.
