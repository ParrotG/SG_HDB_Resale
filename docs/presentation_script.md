# Presentation script

This script is written for approximately 11 minutes 20 seconds at a clear presentation pace. Replace Git contributor names with the members' real names before recording.

## Slide 1 — The question behind a town price map

**ParrotG:**

Our project asks a simple question with an easy-to-misread answer: when one HDB Town has a higher resale price than another, how much of that difference reflects location, and how much reflects the kinds of flats sold there?

We use 222,066 resale registrations from January 2017 through December 2025. Our main comparison is PASIR RIS against BEDOK. In the raw Town model, PASIR RIS appears about 26 percent more expensive. After we compare transactions on time and housing characteristics, the estimate becomes about 12.5 percent lower. Our story is about how data preparation changes interpretation, prediction, and governance—not about building the most complex model.

## Slide 2 — Data quality: small counts, mandatory decisions

**ParrotG:**

We began with literal checks before converting any fields. Pandas found no missing values, blank strings, outer whitespace, label variants, or numeric parse failures. That clean surface did not mean the data required no decisions.

There were 308 groups of exactly identical public rows: 307 pairs and one triplet. Together they created 309 excess copies. Because no transaction identifier or unit number is available, we cannot prove whether identical rows are separate sales. For a conservative modelling frame, we kept one representative from each group and removed the excess copies.

We also converted Remaining Lease to fractional years and compared it with 99 minus the elapsed years since lease commencement. We removed 128 records that differed by more than one year because their cause could not be resolved. This leaves 221,629 rows, or 99.803 percent of the source. Assertions confirm that excluded indices never return in the later analytical or modelling frames.

We did not automatically delete valid statistical tails. Removing high-price training records slightly improves one aggregate result but worsens MAE for expensive test transactions by about 4,009 dollars. Those records represent a real market segment, so they remain.

## Slide 3 — Encoding follows the meaning of each field

**ParrotG:**

Our encoding choices follow what each variable means. Flat Type and Flat Model are labels, so we use one-hot categorical controls. The pie charts show the composition without changing the underlying categories.

Storey Range means the three-floor band containing the flat. We encode its order for summaries, but use categories in the hedonic regression so the model does not assume that every move of three floors has the same price effect.

Remaining Lease becomes fractional years. Month becomes registration time plus calendar controls. Resale Price is strongly right-skewed; the log transform reduces skewness from 0.959 to 0.038 and gives percentage-style regression coefficients.

Finally, an address is not Block alone. We use the hierarchy Town, Street, and Block. Historical target encodings use only earlier years and shrink sparse blocks toward their street and Town parents.

## Slide 4 — Imbalance changes what “average performance” means

**YuyaoWu61:**

The sample is not evenly distributed. Four-room flats make up 42.3 percent of transactions, while 1 ROOM and MULTI-GENERATION each have fewer than 100 records. Town and Flat Type combinations are also uneven, as the heatmap shows. No category is completely new in the 2025 test set, but small groups still produce unstable coefficients and errors.

We therefore report transaction-weighted metrics and equal-Town metrics. In the standard model, a Town with more transactions has more influence. We also fit weighted least squares with inverse Town frequency, so every Town has equal total weight. That reduces Town macro-MAE from 48,728 to 47,265 dollars and reduces mean overprediction from 14,603 to 7,535 dollars.

The two models answer different questions: performance for the average recorded sale versus performance for the average Town. We report both rather than treating one weighting scheme as universally correct.

## Slide 5 — Hedonic pricing and the M0–M4 sequence

**YuyaoWu61:**

We use hedonic pricing because a flat is a bundle of attributes. Its observed price is associated with location, size, type, model, storey, lease, and market time. A hedonic regression lets us hold these observed attributes constant step by step.

M0 contains Town only. M1 adds registration month. M2 adds log floor area. M3 adds Flat Type and Flat Model. M4 adds Storey Range and remaining lease. Every model uses the same 221,629 rows, and uncertainty is clustered by the public building address.

The Town coefficients are conditional associations. They do not estimate the causal effect of physically moving an identical flat from one Town to another, because renovation, accessibility, view, and other unobserved attributes remain outside the data.

## Slide 6 — The non-obvious finding survives stronger comparisons

**YuyaoWu61:**

The PASIR RIS path is our central non-obvious finding. Relative to BEDOK, its coefficient moves from plus 26.0 percent in M0 to plus 26.5 after time controls, then to minus 6.3 after adding area, minus 10.2 after Type and Model, and minus 12.5 after Storey and lease.

In that chosen sequence, the area step accounts for 84 percent of the movement from M1 to M4. But correlated controls can absorb the same information. Across all six entry orders, area's share ranges from only 1.1 to 84.0 percent. Adding Type and Model first also reverses the sign. We therefore conclude that housing composition matters, while refusing to call 84 percent an independent area effect.

We also restrict both Towns to 4 ROOM, Model A flats and then to joint support cells based on year, storey, area, and lease. In the strictest sample, the adjusted difference remains negative 10.8 percent, with a 95 percent interval from minus 13.3 to minus 8.2. This supports a housing-composition reversal. It is an omitted-variable reversal, not a claimed Simpson's paradox and not a causal Town effect.

## Slide 7 — Minimal versus systematic preparation

**drury:**

Next, we test whether preparation changes out-of-time prediction while keeping the model class fixed as ordinary least squares. Development uses 2018 to 2023, 2024 selects the time trend, and 2025 is the test year. Every variant uses the same cleaned rows.

B0 is minimal: raw price and area, ordinal storey, and linear lease and time terms. B1 adds Flat Model and categorical storey. B2 adds log area and a quadratic lease term. B3 changes the target to log price with a smearing correction. B4 adds chronological hierarchical address encoding.

MAE falls from 59,789 dollars in B0 to 46,298 in B4, a 22.6 percent reduction. The large improvements come from functional-form preparation, the log target, and address information. But overall MAE is only one piece of evidence, so we then inspect where the final model fails.

## Slide 8 — Aggregate improvement concealed local failure

**drury:**

B4 improves the overall average but performs worse in BUKIT BATOK and TAMPINES. Relative to B0, their MAE rises by 20,310 and 10,873 dollars. This deterioration appears in all twelve months and is concentrated in common 4 ROOM and 5 ROOM transactions rather than only rare labels.

Replacing 2025 Flat-Type shares with 2024 shares explains only 755 dollars in BUKIT BATOK and 357 in TAMPINES. So a changed Flat-Type mix is not an adequate explanation.

The largest problem appears when the nominal historical address feature enters. From B3 to B4, overall MAE improves by only 934 dollars, while signed error moves from almost zero, plus 330, to overprediction of plus 14,603. A decomposition and frozen-history sensitivity show that recent nominal historical prices raise predictions. Because we selected these Towns after seeing the test results, this is exploratory error analysis, not proof of a causal mechanism.

## Slide 9 — Remove market time from the address feature

**TomoyoCin:**

That diagnosis motivates a revised address feature. A nominal historical price average mixes location with the market level of the years that happened to enter its history. The regression already has time controls, so this can duplicate market-time information.

We compare no address, the nominal encoding, a deflated encoding, and N3, which hierarchically encodes residual location information from an auxiliary quality-adjusted model. Every encoding for year Y uses only years before Y. We choose between the new encodings using 2024 validation MAE, before reading their 2025 result.

N3 reduces the feature's correlation with time from 0.195 to minus 0.001. On 2025, MAE is 47,232 with no address, 46,298 with the nominal address, and 31,606 with the residual address.

A four-year rolling-origin check adds an important qualification. N3 has the lowest MAE in three of four years, but no variant is consistently unbiased. From 2022 to 2024, even the no-address model underpredicts, showing that the main calibration failure belongs to extrapolating the time trend in a rising market. We select N3 for accuracy, not as a universal bias correction.

## Slide 10 — Governance: block precision has a measurable cost

**TomoyoCin:**

The address result also creates a governance question: how much public precision is necessary? A record is unique when no other record shares its Town, Street, Block, Flat Type, storey band, and month. At the released precision, 95.1 percent of cleaned records are unique on these quasi-identifiers.

If location stops at Street, uniqueness falls to 60.1 percent. The prediction test shows that Street-level residual encoding retains 74.5 percent of the full address accuracy gain. Adding Block reduces MAE by another 3,989 dollars, but raises uniqueness by 35 percentage points.

This does not decide publication policy by itself. It makes the trade-off measurable: Block carries a large privacy cost for a smaller marginal accuracy gain in this specification. Street-level release is therefore a defensible option for further policy evaluation.

## Slide 11 — What the evidence changes

**TomoyoCin:**

Our main lesson is that preparation changes the claim we are able to make. A raw map suggested a PASIR RIS premium; comparable housing attributes reversed that interpretation. Consistent exclusion rules kept integrity issues out of every model. The prediction ladder showed a large aggregate gain, but subgroup analysis exposed Town-level failure. Time-normalizing the address feature then improved accuracy without pretending to solve all future market bias.

The evidence remains observational. Renovation, exact accessibility, view, buyer attributes, and detailed building condition are unavailable, and the maps use planning-area proxies.

**Suggested closing line, one sentence per member:**

- **ParrotG:** Profiling turned apparently clean data into explicit, auditable decisions.
- **YuyaoWu61:** Sequential controls revealed a composition reversal and the limits of attributing it to one feature.
- **drury:** Error analysis showed why overall MAE cannot stand in for reliability.
- **TomoyoCin:** Validation and governance analysis converted that failure into a better feature and a measurable privacy trade-off.
