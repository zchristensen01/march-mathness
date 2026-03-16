# NCAA March Madness prediction algorithm audit

**Your model has several strong foundations but needs significant recalibration.** The most critical fixes: AdjEM weight at 29% is too low (research supports 35–45%), historical conference penalties should be eliminated entirely, and the Conference Strength Index should not multiply efficiency-based scores. The 60/40 CDF/Elo win probability blend is defensible but could benefit from fat-tail adjustments. Barttorvik.com turns out to be a goldmine — it offers nearly every data field you're looking for, completely free, including experience metrics, player BPM, venue splits, and coach tournament history. Below is the complete audit across all ten areas.

---

## 1. AdjEM at 29% is significantly underweighted

Research across Kaggle March ML Mania competitions, academic papers, and Nate Silver's COOPER system consistently identifies **Adjusted Efficiency Margin as the single most predictive feature** for tournament outcomes. A 2024 FormulaBot analysis found AdjEM had the highest positive correlation with reaching the Sweet Sixteen of any advanced metric, outperforming seed. Multiple Kaggle gold solutions (2023–2025) rank efficiency metrics as #1 or #2 in feature importance. The 2025 arXiv deep learning study (LSTM + Transformer architectures) hit an AUC of **0.8473** with efficiency-based features as the backbone, confirming a persistent "glass ceiling" at ~75% prediction accuracy across all ML approaches.

**Recommended weight recalibration for a composite power score:**

| Component | Current | Recommended | Rationale |
|-----------|---------|-------------|-----------|
| AdjEM | 29% | **35–45%** | Strongest single predictor across all studies |
| Barthag | Separate | **Merge with AdjEM or drop** | Highly correlated with AdjEM; double-counting if both weighted heavily |
| SOS | Unknown | **8–15%** | Already partially baked into "adjusted" metrics |
| Seeds/rankings | Unknown | **15–25%** | Preseason polls add genuine wisdom-of-crowds value |
| Defense vs offense split | Equal? | **55/45 defense** | Champions averaged 3rd-best defense vs 9th-best offense (2008–2017); balanced teams significantly outperform unbalanced ones per Harvard Sports Analysis Collective |

The critical insight on Barthag: it's derived from the same efficiency inputs as AdjEM using a Pythagorean formula (exponent **11.5** for Torvik, **10.25** for KenPom). Including both AdjEM and Barthag at high weights is redundant. Either use AdjEM as the efficiency backbone at ~40% and exclude Barthag, or use Barthag as a composite at ~35% alongside independent features. The combined "efficiency bucket" should total **50–60%** of the power score.

**Balance is the strongest signal for tournament success**, more than raw offensive or defensive dominance. Harvard's PASE analysis found offense-focused teams underperform by 0.15 wins and defense-focused teams by 0.12 wins relative to seed expectations. Only the offensive underperformance was statistically significant. Flag any team where the gap between AdjO rank and AdjD rank exceeds **30 positions** — every champion from 2008–2017 stayed within this threshold.

---

## 2. Barttorvik is the single most valuable free data source

Barttorvik.com provides **every data field you asked about**, completely free, with bulk CSV/JSON downloads and two mature R packages (toRvik and cbbdata) for programmatic access. No paywall exists on any data.

**Specific field availability — confirmed:**

| Data field | Available? | How to access |
|-----------|-----------|---------------|
| Experience (Exp) column | **Yes** | Player-level `exp` field (Fr/So/Jr/Sr); team-level experience metric weighted by minutes; returning possession minutes at `rpms.php` |
| Bench minute percentages | **Partial** | `bench_pts` in team box scores; individual player minutes available to derive bench minutes % |
| Player-level BPM | **Yes** | `bpm`, `obpm`, `dbpm` all available at the player-game level via advanced stats endpoint |
| Shooting splits by venue (H/A/N) | **Yes** | Four factors filterable by venue via `bart_factors(venue='home')` or URL parameter |
| Recent form (last 10 games) | **Yes** | `lastx=10` parameter or custom date-range filtering on trank page |
| Height/physicality | **Yes** | Player `hgt` field; recruiting data includes height AND weight |
| Free throw rate | **Yes** | `off_ftr` and `def_ftr` in four factors for offense and defense |
| Road win records | **Yes** | Venue filtering isolates away games with W/L records |
| Coach tournament experience | **Yes** | Dedicated page at `/cgi-bin/ncaat.cgi?type=coach` |

**Bulk data endpoints** (no scraping needed):
- Team season stats: `barttorvik.com/YYYY_team_results.csv`
- Player advanced stats: `barttorvik.com/getadvstats.php?year=YYYY&csv=1`
- Team slice data (by game type): `teamslicejson.php?year=YYYY&csv=1&type=R`
- Historical daily ratings: `/timemachine/team_results/YYYYMMDD_team_results.json.gz`
- Returning possession minutes: `YEAR_rpm.json`

**KenPom** is mostly paywalled (~$20/year). The free main page shows overall rankings with AdjEM, AdjO, AdjD, AdjT, Luck, and SOS for all 365 teams. Paid subscription adds player stats, bench minutes %, average height, matchup projections, and experience metrics. **ESPN BPI** is 100% free with BPI rating, Strength of Record, and game predictions. **Sports-Reference** provides SRS (Simple Rating System) free at `/cbb/seasons/men/2025-ratings.html`. **Warren Nolan** offers free NET rankings, RPI, Elo ratings, and quad records.

The optimal free stack: **Barttorvik (primary) + Sports-Reference (SRS, validation) + ESPN BPI (independent power rating)** covers the vast majority of what KenPom offers paid.

---

## 3. Conference Strength Index should not multiply efficiency-based scores

This is the most clear-cut finding in the audit. **Applying CSI to efficiency-derived scores creates confirmed double-counting**, and the research unanimously supports removing it from those components.

The logic is straightforward: KenPom, Torvik, and BPI all solve for opponent-adjusted efficiency by iterating across all 353 D-I teams simultaneously. Conference strength is already embedded in every team's AdjEM. KenPom's own blog acknowledged this explicitly: "The system tended to give teams that dominated weak conferences a bit too much credit" — which was fixed by changing weighting coefficients within the efficiency calculation itself, not by adding an external penalty.

Ben Wieland's 2024 simulation study at bbwieland.github.io provides the most rigorous analysis. He created synthetic teams with known true efficiencies, simulated full seasons with conference structures, and found that conference scheduling "bubbles" do create slight systematic distortion — but the fix is better calibration of the efficiency model, **not a blunt external multiplier**.

**Where CSI might have marginal value:** Only on components that don't already adjust for opponent quality, such as raw win-loss record, raw point differential, or resume-based metrics like WAB. Even then, it should be **additive, not multiplicative**. KenPom explicitly moved from multiplicative to additive adjustments after finding that multiplicative frameworks disproportionately penalize or reward extreme teams.

**Recommended approach:** Replace the CSI multiplier entirely with a **seed-vs-metric discrepancy score**. Calculate the gap between a team's NCAA seed and their KenPom/Torvik ranking. A 3-seed ranked 22nd on KenPom is more predictive of underperformance than "they're from Conference X." This captures the same overseeding signal without circular logic.

---

## 4. What makes bracket picks interesting versus chalk

The strongest upset predictors, ranked by evidence quality across multiple studies:

**Tempo is the sleeper variable nobody weights enough.** Splash Sports' analysis of 11 first-round marquee upsets (2021–2023) found **9 of 11 upset victims ranked outside the top 100 in adjusted tempo** — and 7 of 9 were beyond 200th. Slow-tempo favorites limit possessions, which compresses scoring variance and gives underdogs a fighting chance in every game. This isn't about fast underdogs beating slow favorites; it's about slow favorites being uniquely vulnerable.

**Road/neutral performance is a fraud detector, not just a nice-to-have.** Iowa State lost one round earlier than their seed indicated in three consecutive tournaments (2023–2025), with ESPN noting they "tend to underperform in March due to a massive home-court advantage." Kansas State in 2023 went 16-1 at home but 7-9 away — classic overseeding from inflated home records. Since every tournament game is on a neutral court, road+neutral record is a far better predictor than overall record.

**Experience findings are nuanced.** Generic class-year experience shows essentially zero correlation with tournament overperformance (R² = 0.0002 per Harvard 2019). But **tournament-specific experience** — returning minutes from players who played in prior NCAA tournaments — is statistically significant per Harvard's Ezekowitz study (2011–2012). The key metric is returning tournament minutes, not simply having upperclassmen.

**Height and rebounding matter.** Offensive rebounding percentage emerged as one of the top predictive features in the Odds Gods LightGBM model (2026). Florida's 2025 championship run was built on being 5th nationally in offensive rebound percentage; their 2026 team leads the country in rebounding margin at **+14.5**. UConn's 2023 title was anchored by glass dominance. Physical teams that crash the boards "usually don't suffer upsets."

---

## 5. Fraud score should add four critical signals

Based on the research, the current fraud detection model is missing several empirically validated signals:

**Home-road split** is the single strongest fraud indicator. Calculate the gap between home record and road record. Teams with a massive differential (like Kansas State 2023 at 16-1 home, 7-9 away) are systematically overseeded because the committee's resume metrics overweight home wins. This should be a primary fraud input.

**Late-season form decline** predicts tournament failure. The Odds Gods model explicitly weights recent 5-game scoring margin as a feature. In the 2026 bracket, Florida lost by 17 in the SEC semifinal, Missouri lost 3 straight entering the tournament, and Clemson lost 5 of 7 late — all flagged as vulnerable despite decent seeds. Compute a momentum score comparing last-10-game efficiency to full-season efficiency.

**Free throw rate allowed (defensive FTR)** is an underused fraud signal. Teams that allow opponents to the free throw line at high rates become increasingly vulnerable as tournament games tighten in the second half. Kansas State 2023 was specifically flagged for this. Conversely, underdogs who get to the line (like VCU 2026, top-20 nationally in FTR) stay competitive in close games.

**Three-point dependency is NOT a fraud signal — it's a variance flag.** Multiple studies confirm no systematic relationship between 3-point shooting rate and tournament underperformance (R² ≈ 0.001). However, in actual upsets, underdogs who won shot **5.5% above** their season 3PT average while favorites who lost shot **5.5% below** — a ~7-point swing that was the largest single effect found in upset analysis. You can't predict which way it breaks, but you can flag 3-point-dependent teams as **high-variance** rather than "likely to fail."

**Proposed fraud score components:**

- Seed-vs-KenPom/Torvik rank discrepancy (highest weight)
- Home-road record differential
- Late-season form decline (last 10 vs full season)
- Defensive FTR allowed (high = vulnerable)
- Coach tournament underperformance history
- Offensive-defensive balance gap (offense-heavy = fraud risk)
- Close-game record regression (teams 6-2 in overtime/close games regress)

---

## 6. Cinderella score needs tempo, turnovers, and coaching

The research identifies a remarkably consistent Cinderella profile across decades of tournament data. **The ideal upset candidate controls tempo, forces turnovers, defends well, and has a coach who has been there before.**

**Slow, controlled tempo** on the underdog's side correlates with Cinderella runs. Mid-Major Madness found that "historically, mid-major teams that make long tournament runs control the tempo, not push the pace." St. Peter's 2022 was 249th in tempo and reached the Elite Eight. Fewer possessions mean fewer chances for the better team's talent advantage to manifest.

**Turnover differential is a key differentiator.** In the 2023 FDU-over-Purdue upset (16 over 1), Purdue turned the ball over 16 times for 15 FDU points, while FDU ranked 32nd nationally in forced turnovers. UC San Diego (2026) is #1 nationally in turnover margin (+7.2) — a classic Cinderella trait.

**The 12-5 matchup** remains the sweet spot for upsets at a roughly **35% historical upset rate**, with 50% of 12-5 games going to the 12-seed in 2025. This matchup consistently produces upsets because 5-seeds are often from power conferences with inflated resumes, while 12-seeds are frequently conference tournament champions riding momentum with nothing to lose.

**Coach tournament experience is real and measurable.** On the fraud side: Rick Barnes has had 18 of 27 tournament trips end with a loss to a lower seed; Matt Painter's teams lost to seeds 13+ three straight years; T.J. Otzelberger's Iowa State lost one round earlier than seed in 3 consecutive tournaments. On the Cinderella side: Ben Jacobson (Northern Iowa) has a history of first-round upsets (2010 vs Kansas, 2015, 2016), and Rick Pitino (St. John's) carries March pedigree. Barttorvik provides coach tournament data at `/cgi-bin/ncaat.cgi?type=coach`.

**Proposed Cinderella score components (seeds 9–16):**

- Defensive efficiency relative to seed (high weight)
- Seed-vs-predictive-metric gap (underseeded by analytics)
- Opponent tempo rank (slow-tempo favorites are vulnerable targets)
- Turnover margin / forced turnover rate
- Free throw shooting % (late-game clutch)
- Road/neutral win record
- Returning tournament minutes (not generic experience)
- Coach tournament track record
- Recent form / momentum (conference tournament run)
- Offensive rebounding rate

---

## 7. Power rankings should show three distinct views

The consensus from examining KenPom, Torvik, COOPER, and ESPN BPI display approaches supports offering **three complementary views**, each serving a different analytical purpose:

**View A — Pure efficiency ranking** based solely on AdjEM (or Barthag). This mirrors KenPom's primary ranking and answers "which team is fundamentally the best?" No conference adjustments beyond what's already in the opponent-adjusted calculation. Sortable by AdjO, AdjD, AdjT, and balance score. This is the analytical backbone.

**View B — Composite ranking** incorporating momentum (last-10-game efficiency delta), SOS, injury impact, and road/neutral record. This answers "which team is best right now for predicting today's game?" This is the game-prediction view and should weight recent form at roughly **15–20%** alongside the efficiency core.

**View C — March Madness specific ranking** that applies tournament-relevant adjustments: balance flag, coach tournament history, experience metrics, tempo vulnerability scores, fraud/Cinderella indicators, and historical seed-line performance. This answers "which teams will over/underperform their seed in March?" This view should include round-by-round advancement probabilities from Monte Carlo simulations.

Best practices from leading sites: color-code offensive vs defensive strength, include upset probability flags, show the gap between seed and analytics ranking prominently, and allow sorting by any column. Torvik's approach of filterable date ranges and venue splits is particularly effective for users who want to investigate specific scenarios.

---

## 8. The 2026 bracket and community model predictions

The 2026 NCAA Tournament bracket (released March 15–16, 2026) features **Duke, Arizona, Michigan, and Florida as 1-seeds**. Duke is the #1 overall seed at 32-2 with a KenPom adjusted net rating of **+40.61** (best since 1999 Duke), but faces critical injuries to starters Caleb Foster (broken foot, out) and Patrick Ngongba II (foot, questionable). Arizona (32-2) won the Big 12 regular season and tournament with two likely lottery picks and is on a 9-game winning streak — widely considered the safest 1-seed.

**Community consensus on overvalued teams:** Duke (injuries make them extremely vulnerable despite #1 overall), Purdue (rose to 2-seed after Big Ten tournament upset but profile "more in line with a 3-seed"), and Arkansas (4-seed with defense ranked only 46th). Memphis and Michigan also flagged by EvanMiya metrics as overseeded.

**Community consensus on undervalued teams:** Miami of Ohio (31-1 record placed in the First Four — controversial), St. John's (5-seed with Big East regular season + tournament titles, beat UConn twice, ranked 13th AP), BYU (6-seed with projected #1 NBA draft pick AJ Dybantsa), VCU (16-1 in last 17 games, won A-10 title, 39th nationally per Torvik), and Texas Tech (5-seed still competitive despite losing star JT Toppin to ACL tear).

**Most popular upset picks across models and experts:** Akron (12) over Texas Tech (5), VCU (11) over North Carolina (6, missing Caleb Wilson), TCU (9) over Ohio State (8), Hawaii (13) over Arkansas (4), and Santa Clara (10) over Kentucky (7). SportsLine's model projects one region where the 1-seed does NOT make the Final Four and predicts two double-digit seed upsets in a single region.

The Kaggle March ML Mania 2026 competition is active with Brier score evaluation. Community approaches range from simple logistic regression on strength differentials to neural networks with 100+ features. The most successful GitHub models combine KenPom, Torvik, and Massey ordinals as inputs.

---

## 9. Historical conference penalties must be removed

**The Big Ten fraud penalty (0.65) and ACC penalty (0.25) are not supported by research and should be eliminated immediately.** Three independent lines of evidence converge on this conclusion.

First, the Harvard Sports Analysis Collective (2015) ran regression analysis on KenPom data from 2002–2014 and found **no conference showed statistically significant seeding bias at the 5% level**. The Big Ten's coefficient was actually *positive* (+0.345, p=0.108), meaning the committee had historically *undervalued* them. The ACC's coefficient was negative (-0.176, p=0.429) but nowhere near significant.

Second, conference effects show extreme year-to-year variance that makes fixed penalties meaningless. The Big Ten went from the **best tournament conference in history** (+24.1 PASE from 2000–2019, nearly double any other league) to the **worst single-year performance ever** (-6.63 PASE in 2021). The ACC posted +8.03 PASE in 2022 (3rd-best single-year ever). The Big 12 dropped to -5.63 PASE in 2024 (5th worst ever). These wild swings confirm that conference tournament performance is high-variance noise, not a persistent effect.

Third, academic research directly contradicts the ACC penalty. Zimmer & Kuethe (2008, Economics Bulletin) found that ACC teams were "commonly seeded to positions lower than predicted" — the committee was already penalizing them. Ben Wieland (2024) confirmed the ACC leads the NCAA with almost **13 more wins than expected** via predictive metrics from 2010–2023.

**The proper replacement:** Use current-year ensemble rating system disagreement as a proxy for conference calibration uncertainty. When KenPom, Torvik, BPI, and Massey disagree significantly on a team's rating, that signals potential conference calibration issues worth flagging — without the crude assumption that an entire conference's teams will systematically underperform.

---

## 10. The 60/40 win probability blend is reasonable but improvable

The current 60% normal CDF spread model + 40% Elo logistic model is a defensible approach that mirrors industry practice. Both methods are standard in the literature, and blending them smooths each method's weaknesses. But three specific improvements would increase calibration.

**Add fat tails to the normal CDF component.** COOPER (Nate Silver, 2026) uses a Student's t distribution rather than a pure normal CDF, finding it provides better calibration for outlier scores. A normal distribution underestimates upset probability in extreme mismatches because its tails are too thin. Using a Student's t with **8–10 degrees of freedom** better captures the reality that 16-seeds occasionally beat 1-seeds and blowouts happen more often than a Gaussian predicts.

**Consider adjusting toward 50/50 for tournament games specifically.** Tournament conditions are more standardized (neutral courts, concentrated timeframe, high stakes) than the regular season. The Elo logistic component handles these conditions slightly better because it naturally accounts for the fact that large rating gaps don't translate as reliably to outcomes in single-elimination settings.

**The standard conversion formulas for reference:**
- **Spread-based (CDF):** `Spread = 1.1 × (AdjEM₁ - AdjEM₂) × (Tempo₁ + Tempo₂) / 200`, then `P = Φ(Spread / 11)` where 11 is the standard deviation and 1.1 is the "blowout inflation" factor from Breiter & Carlin (1997)
- **Elo logistic:** `P = 1 / (1 + 10^(-Elo_diff × 30.464/400))` per FiveThirtyEight's formula
- **KenPom Log5:** Calculate Pythagorean expectations for each team, then `P(A wins) = (pA - pA×pB) / (pA + pB - 2×pA×pB)`

Silver's current COOPER system simplified to a **5/8 COOPER + 3/8 KenPom** blend for tournament forecasts, down from the six-system ensemble FiveThirtyEight previously used. The rationale: fewer systems means fewer error opportunities, and COOPER + KenPom already capture most of the predictive signal. Adding more rating systems yields diminishing returns — the correlation between KenPom, Torvik, and BPI is very high, so each additional system adds less unique information than the first two.

---

## Conclusion: five changes that will most improve the model

The audit reveals that the model's architecture is sound but several calibration choices are working against prediction accuracy. **Raise AdjEM weight to 35–45%** and treat the efficiency bucket (AdjEM + any Barthag-derived signal) as the dominant input at 50–60% of total power score. **Remove all historical conference penalties** — they lack statistical support and conference effects don't persist year-to-year. **Stop multiplying efficiency-based scores by CSI** — opponent-adjusted metrics already account for conference strength, and the multiplicative approach creates confirmed double-counting. **Add home-road split, late-season form, and defensive FTR allowed to the fraud score** — these are empirically the strongest overseeding indicators that the model currently lacks. **Add tempo vulnerability, turnover margin, and coach tournament history to the Cinderella score** — the 9-of-11 upset victim tempo finding alone could meaningfully improve upset detection.

The 2026 bracket offers immediate testing opportunities: Duke's injuries create a natural experiment on how well the model handles injury-adjusted overseeding, Arizona profiles as the safest 1-seed across every metric, and the 12-5 matchups (especially Akron-Texas Tech) are classic Cinderella detection scenarios. Barttorvik provides every data field needed to implement these changes — for free — making the data acquisition barrier essentially zero.