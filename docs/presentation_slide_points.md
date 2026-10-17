# Presentation slide points

Target duration: **11 minutes 20 seconds**. The final 40 seconds are a safety margin under the 12-minute limit. The presenter assignments use Git contributor names and can be replaced with members' real names.

## Slide 1 — The question behind a town price map (0:00–0:45, ParrotG)

- **Question:** How much of an observed HDB Town price difference reflects location, and how much reflects the mix of flats sold?
- 222,066 resale registrations, January 2017 to December 2025.
- Central result: PASIR RIS changes from **+26.0%** to **-12.5%** relative to BEDOK after controls.
- Treat machine learning as evidence about preparation decisions, not as the goal.

Visual: [Town premiums before and after controls — dark version](../figures/06_town_premium_maps_dark.png)

## Slide 2 — Data quality: small counts, mandatory decisions (0:45–1:40, ParrotG)

- No missing values, blank strings, outer whitespace, label variants, or numeric parse failures.
- 308 exact-duplicate groups contain 617 rows; keep one representative and remove **309 excess copies**.
- Remove **128 lease-inconsistent records** where recorded lease differs from the 99-year identity by more than one year.
- Final analytical frame: **221,629 rows, or 99.803% of the source**.
- Valid price tails remain: trimming them worsens high-price test MAE by **SGD 4,009**.

Visual: use a compact table from notebook Sections 3–4. Backup distribution visual: [Numeric distributions](../figures/03_numeric_distributions.png)

## Slide 3 — Encoding follows the meaning of each field (1:40–2:40, ParrotG)

- Flat Type and Flat Model: categorical one-hot controls; pie charts describe composition.
- Storey Range: ordinal for summaries, categorical in regressions to avoid assuming equal price steps.
- Remaining Lease: fractional years; Month: registration time and calendar controls.
- Price: log transform reduces skewness from **0.959 to 0.038**.
- Address: Town → Street → Block hierarchy with earlier-year-only smoothing.

Visuals: [Category shares](../figures/01_category_shares.png) and [Storey shares](../figures/02_storey_shares.png)

## Slide 4 — Imbalance changes what “average performance” means (2:40–3:35, YuyaoWu61)

- 4 ROOM accounts for **42.3%** of records; 1 ROOM and MULTI-GENERATION each contribute fewer than 100 rows.
- Town × Flat Type support is uneven, although 2025 has no entirely unseen category.
- Report transaction-weighted and equal-Town metrics.
- Equal-Town WLS lowers Town macro-MAE from **SGD 48,728 to 47,265** and signed error from **+14,603 to +7,535**.
- No synthetic oversampling is needed for an interpretable regression.

Visual: [Town × Flat Type support heatmap](../figures/04_representation_support.png)

## Slide 5 — Hedonic pricing and the M0–M4 sequence (3:35–4:30, YuyaoWu61)

- Hedonic pricing decomposes a home's observed price into associations with its attributes.
- M0: Town only; M1: + registration month; M2: + log area.
- M3: + Flat Type and Flat Model; M4: + Storey Range and remaining lease.
- Same 221,629 rows in every model; building-clustered uncertainty.
- Coefficients are conditional associations, not causal effects of moving a flat.

Visual: [Town coefficient path](../figures/05_town_coefficient_path.png)

## Slide 6 — The non-obvious finding survives stronger comparisons (4:30–5:55, YuyaoWu61)

- PASIR RIS path: **+26.0%, +26.5%, -6.3%, -10.2%, -12.5%** from M0 to M4.
- In the chosen order, area supplies **84.0%** of the M1–M4 movement.
- Across all control orders, area's share ranges from **1.1% to 84.0%**; Type/Model first also reverses the sign.
- Strict joint-support sample: **-10.8%**, 95% CI **-13.3% to -8.2%**, 387 transactions.
- Conclusion: a housing-composition reversal; not a causal location effect and not a claimed Simpson's paradox.

Visuals: [Control-order sensitivity](../figures/09_control_order_sensitivity.png) and [Common-support sensitivity](../figures/08_common_support_sensitivity.png)

## Slide 7 — Minimal versus systematic preparation (5:55–7:05, drury)

- Same OLS method, chronological split, cleaned rows, and 2025 test set for every variant.
- B0 minimal: raw price/area, ordinal storey, linear lease/time.
- B1 categorical structure; B2 functional forms; B3 log target; B4 nominal historical address.
- 2025 MAE falls from **SGD 59,789 to 46,298**, a **22.6%** reduction.
- Improvement is evidence for preparation choices; subgroup errors and calibration still matter.

Visual: [B0–B4 preparation comparison](../figures/12_preparation_comparison.png)

## Slide 8 — Aggregate improvement concealed local failure (7:05–8:15, drury)

- B4 worsens MAE in BUKIT BATOK by **SGD 20,310** and TAMPINES by **SGD 10,873** versus B0.
- The deterioration persists through all twelve months and lies mainly in common 4 ROOM and 5 ROOM groups.
- Flat-Type share standardization explains only **SGD 755** and **SGD 357**.
- Nominal address encoding improves overall MAE slightly versus B3 but shifts signed error from **+330 to +14,603**.
- This is an exploratory diagnosis; selected subgroups do not prove a causal mechanism.

Visuals: [Overall and town-level stage errors](../error_analysis_outputs/01_stage_error.png) and [Address mechanism](../error_analysis_outputs/04_address_mechanism.png)

## Slide 9 — Remove market time from the address feature (8:15–9:45, TomoyoCin)

- Nominal historical target encoding mixes location with market time already present in the model.
- N3 encodes residual location information from strictly earlier years; selection uses 2024 validation only.
- Feature–time correlation falls from **0.195 to -0.001**.
- 2025 MAE: no address **47,232**, nominal address **46,298**, residual address **31,606**.
- Rolling origins: residual encoding wins MAE in **3 of 4 years**; remaining bias mainly follows the time trend.

Visuals: [Time-normalized address encoding](../section16_outputs/01_time_normalized_address.png) and [Rolling-origin check](../section16_outputs/02_rolling_origin.png)

## Slide 10 — Governance: block precision has a measurable cost (9:45–10:40, TomoyoCin)

- At released block/storey/month precision, **95.1%** of cleaned records are unique on the quasi-identifiers.
- Street-only precision lowers uniqueness to **60.1%**.
- Street encoding retains **74.5%** of the full address accuracy gain.
- Adding Block buys another **SGD 3,989** MAE but raises uniqueness by **35.0 percentage points**.
- A street-level release is a plausible privacy–utility compromise, subject to policy review and further tests.

Visual: [Privacy–utility frontier](../section17_outputs/02_privacy_utility_frontier.png)

## Slide 11 — What the evidence changes (10:40–11:20, TomoyoCin; closing line from each member)

- Raw Town price maps can mislabel housing composition as a location premium.
- Integrity rules must remain consistent across EDA, inference, and prediction.
- Overall accuracy can conceal Town-level error and time leakage.
- The strongest result is the reasoning chain: profile → prepare → challenge → revise → validate.
- Limits: observational data, omitted renovation/accessibility variables, planning-area map proxies, and imperfect future time trends.

Visual: [PASIR RIS coefficient path](../figures/05_town_coefficient_path.png)

### Optional backup slides

- [Common-support distributions](../figures/07_common_support_distributions.png)
- [M4 diagnostics](../figures/11_m4_diagnostics.png)
- [Storey coefficients](../figures/10_storey_effects.png)
- [Monthly subgroup errors](../error_analysis_outputs/02_monthly_error.png)
- [Disclosure-risk grid](../section17_outputs/01_disclosure_risk.png)
