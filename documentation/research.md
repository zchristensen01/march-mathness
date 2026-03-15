# Validating and tuning NCAA tournament prediction engines

**The most impactful adjustments to a March Madness prediction model involve resolving the tempo paradox correctly, recalibrating 6-vs-11 seed priors to reflect a near-coin-flip in the modern era, letting ML models learn feature weights rather than fixing them manually, and building a structured "fraud score" around offensive-defensive imbalance and luck regression.** These findings draw on the UC Berkeley Sports Analytics Group (Toohey, 2025), Harvard Sports Analysis Collective (Ezekowitz & Cohen, 2010), Kaggle March ML Mania winning solutions (2018–2025), FiveThirtyEight methodology, and Barttorvik tournament performance data. Below is a point-by-point analysis of all eight research questions with specific numbers, citations, and actionable recommendations.

---

## 1. The tempo-upset paradox is real but resolvable

The apparent contradiction between the Berkeley and Harvard findings dissolves once you recognize they measure **different things**. Toohey's 2025 Berkeley study ("The Art of the Underdog," Sports Analytics Group at Berkeley, May 2025) analyzed *team profiles* of double-digit seeds making the Sweet 16 from 2015–2025 using K-means clustering. His conclusion: Cinderella archetypes that succeed have **lower season-long adjusted tempo**, balanced and efficient offense, high mid-range shooting volume, and dominant paint play. The archetype most likely to flame out is the fast-tempo, transition-heavy underdog.

The Harvard study (Ezekowitz & Cohen, "Putting Theories to the Test," Harvard Sports Analysis Collective, February 2010) measured something else entirely: the *in-game tempo of individual upset games* from 2004–2009. Across 144 upset-eligible games (35 upsets), upset games averaged **67.77 possessions vs. 64.93 in non-upsets** — a difference of ~2.84 possessions, with p=0.0134. Logistic regression showed each extra possession increased upset odds by **7.7%** (p=0.021). The authors ruled out late-game fouling as a confounder (r²=0.043 between margin and tempo).

**The reconciliation**: Slow-tempo team *profiles* produce more Cinderellas because controlling pace reduces variance and keeps games close — consistent with Dean Oliver's theoretical framework and Brian Skinner's mathematical proof ("Scoring Strategies for the Underdog," *Journal of Quantitative Analysis in Sports*, 2011) that fewer possessions increase outcome variance favoring underdogs. But when upsets *actually occur*, the game tempo tends to run slightly higher, likely because the favorite loses ball control (turnovers were the strongest single predictor at p=0.013 in Harvard's model) and the underdog capitalizes in transition.

**Recommendation for your model**: Use **season-long adjusted tempo** as a Cinderella identifier (lower = better for underdogs), but do not penalize higher *in-game* tempo. The tempo *contrast* — the mismatch between an underdog's preferred slow pace and a favorite's preferred fast pace — is the most actionable signal. Toohey's 2025 study is more current (2015–2025 data) and uses modern basketball conditions (30-second shot clock, NIL era), making it the better guide for current predictions. The Harvard data predates the 2015 shot clock change and should be weighted lower.

---

## 2. The 6-vs-11 seed upset rate has reached parity in the modern era

The all-time record (1985–2025, 160 first-round games) stands at **62-98 in favor of 6-seeds, giving 11-seeds a 38.75% win rate**. This figure is confirmed across NCAA.com, Wikipedia's tournament upset database, and PoolGenius/TeamRankings through the completion of the 2025 Round of 64.

The 68-team era tells a dramatically different story. For the confirmed 2014–2025 window (11 tournaments, 44 games), 11-seeds are **23-21 — a 52.3% win rate**, making them slight *favorites*. The last nine tournaments (2016–2025) show 11-seeds at **19-17 (52.8%)**. Adding the strongly 11-seed-favored 2011 tournament (3-1, including VCU's Final Four run), the full 68-team era estimate across 14 tournaments and 56 games is approximately **28-28 to 29-27, or 50–52%**. The user's estimate of ~51–52% is well-supported and essentially correct.

This makes the 6-vs-11 matchup the most upset-prone "true upset" line in the tournament — actually **more dangerous than the famous 5-vs-12 matchup** (35.6% all-time upset rate). The 2025 tournament was historically chalky (only 5 total upsets, fewest since 2007), with Drake over Missouri the sole 11-over-6 result, but this didn't meaningfully alter the post-2011 trend.

**Recommendation**: Your model should treat the 6-vs-11 first-round matchup as essentially a **coin flip** (50-52% for the 11-seed) in the 68-team era, not the ~39% base rate the all-time numbers suggest. Apply similar recalibration to the 8-vs-9 line, where 9-seeds have won **~62.5%** since 2016.

---

## 3. AdjEM at 27% is defensible, but learned weights outperform manual ones

Kaggle March Machine Learning Mania winners consistently avoid manually fixed weights. The 2022 and 2023 winners both used "raddar" code computing a Team Quality metric from game results, deriving probabilities from seed differences and quality differentials. The 2024 winner used Monte Carlo simulation blending third-party ratings with personal intuition. Top 1% solutions (e.g., maze508's 2023 Gold medal approach) feed the **top 10 historically most accurate rating systems** — including KenPom, Sagarin, and Moore — into gradient boosted trees (XGBoost/LightGBM) that learn feature importance automatically.

The most transparent benchmark is FiveThirtyEight's model, which blended **seven rating systems at equal weight (~14.3% each)**: Sagarin, KenPom, LRMC, Sonny Moore, ESPN BPI, committee S-curve, and preseason polls. Their rationale: "There really isn't that much difference between the systems." The Odds Gods LightGBM system (2025–2026) uses KenPom, Moore, Whitlock, Massey, Bihl, and NET as pairwise differences, plus custom Elo and box-score differentials, achieving a **Brier score of 0.153** on the 2025 NCAA tournament.

A key finding from FormulaBot's 2024 Random Forest model (trained on 2012–2023): **AdjEM ranked as the #1 most important feature**, ahead of seeding, SRS, SOS, and point differential. JakeAllenData's 2025 Ridge regression for predicting championship equity ranked AdjEM-related features (top_6_AdjEM binary) as the **3rd most important** behind seed and AdjOE.

**Assessment**: Your 27% AdjEM weight is reasonable and within the range of what models implicitly learn, but it may be slightly conservative if AdjEM is your single strongest predictor. The 12% composite rank weight aligns well with FiveThirtyEight's ~14% committee S-curve weight. The strongest recommendation from 2023–2025 research is to **use 5–8 diverse rating systems as pairwise differences** (Team A minus Team B) in a gradient boosted model, letting cross-validation determine optimal weights. Adding **preseason polls** (surprisingly strong per FiveThirtyEight — teams revert to preseason expectations in March) and **recent form** (last 5–10 games scoring margin) provides marginal but real gains. Top Kaggle ensembles achieve Brier scores of **0.170–0.175**.

---

## 4. Building a fraud score around imbalance, luck, and preseason deviation

Offensive-defensive imbalance is among the strongest fraud indicators, confirmed by multiple sources. The Harvard Sports Analysis Collective's 2021 study ("Balance Wins Championships") found that after controlling for seed and overall efficiency, **offense-heavy unbalanced teams** (AdjO rank ≥50 spots better than AdjD rank) underperformed seed expectations by **0.15 wins per tournament** — a statistically significant result. Defense-heavy imbalance also underperformed (by 0.12 wins) but was not significant.

FiveThirtyEight's championship data reinforces this: **14 of the past 19 champions** (2002–2021) ranked top 15 in *both* AdjO and AdjD. Only 5 of 76 Final Four teams since 2001–02 had defensive efficiency outside the top 50. No top-4 seed with defense ranked 75th or worse has reached the Final Four in the KenPom era. The 2022 Purdue 3-seed (AdjO #3, AdjD #100) lost in Round 1 to 15-seed Saint Peter's — a textbook fraud profile.

The **luck metric** (KenPom's deviation of actual win% from Pythagorean expectation) has a year-to-year correlation of just **0.06**, making it almost pure noise. Providence in 2022 had the #1 luck rating nationally (+0.194), was a 4-seed despite KenPom efficiency suggesting a 13-seed — a 9-seed-line overseeding — and lost in Round 2. Teams with luck above +0.10 on a top-4 seed are historically major red flags.

**Recommended fraud score composite**:

| Feature | Weight | Rationale |
|---|---|---|
| KenPom rank vs. seed deviation | 25% | Directly measures overseeding |
| Offensive-defensive imbalance | 25% | Strongest validated structural predictor |
| KenPom luck metric | 15% | Near-zero persistence; strong regression signal |
| Preseason rank deviation | 15% | FiveThirtyEight: preseason polls are roughly as predictive as in-season performance |
| High-variance style (3PT reliance, TO rate) | 10% | Introduces randomness favoring underdogs |
| Consistency + weak SOS | 10% | Supporting indicators |

Luck should function as a **penalty modifier** rather than a primary input — discount advancement probability by **5–10%** for teams with luck above +0.05.

---

## 5. Cinderella prediction features have converged across recent studies

The Toohey (2025) Berkeley study has **not been formally peer-reviewed or independently validated** — it is a data journalism piece on a student organization blog. However, its findings align with and complement other recent work, lending credibility. The Furman University "Slingshot" ensemble model (Bouzarth, Hutson & Harris, used by ESPN and The Athletic) combines **18 models** and achieves **76% accuracy** on games with seed gaps ≥5, tested on 2007–2021 data. It correctly identified Furman over Virginia in 2023 and flagged Ole Miss, BYU, and Memphis as 40%+ upset-probability teams in 2025.

A Wharton School student paper (2023) on predicting Cinderella teams (seeds 8+ making Sweet 16) correctly gave Florida Atlantic a **19.7% Sweet 16 probability** vs. the 4.7% historical average for 9-seeds. FormulaBot's Random Forest gave 2023 Purdue (#1 seed) only a 22% Sweet 16 probability and Princeton (15-seed) 59% — both validated.

The consensus empirically validated features for **9–12 seed success**, ranked by evidence strength:

- **KenPom AdjEM** — very strong; #1 feature across multiple ML models, more predictive than seeding
- **Defensive efficiency (AdjD)** — very strong; "defense doesn't go cold" is the consistent finding
- **Low turnover rate** — strong; Harvard found 1% decrease in TO% = 26% increase in upset odds (p=0.013)
- **Strength of schedule** — strong; validated by Toohey, FormulaBot, and others
- **Experience/senior leadership** — moderate-strong; consistent across multiple analyses
- **Controlled/slow tempo** — moderate; supported by Toohey and conventional wisdom, contradicted by Harvard's in-game data
- **Mid-range shooting proficiency** — novel and unvalidated; found only by Toohey (2025), potentially a small-sample artifact

One important contextual note: **the NIL era appears to be suppressing Cinderella runs**. Only one Cinderella reached the Sweet 16 in each of 2023, 2024, and 2025. The 2025 Sweet 16 was 100% Power Four teams for the first time ever. Models should potentially adjust Cinderella base rates downward for the post-2021 period.

---

## 6. Isotonic regression yields modest but meaningful Brier improvement

For NCAA tournament prediction specifically, isotonic regression calibration on a reasonably well-built base model (logistic regression or gradient boosted trees) typically provides a **0.005–0.015 Brier score improvement**, roughly **3–8% relative improvement**. The Odds Gods LightGBM system, which explicitly uses isotonic regression on out-of-fold predictions, achieves Brier scores of **0.187 (2024 full season)** and **0.153 (2025 NCAA tournament)**, though uncalibrated baselines aren't separately reported.

The improvement magnitude depends heavily on the base classifier. Poorly calibrated models (SVMs, some neural networks) can see dramatic gains — one benchmark showed SVM Brier improving from **0.178 to 0.052** with isotonic regression. Already well-calibrated classifiers (logistic regression, Vowpal Wabbit) may see zero improvement. For the gradient boosted trees dominant in NCAA prediction, the primary benefit is **correcting overconfidence at the extremes** — ensuring a 1-seed vs. 16-seed isn't assigned 99.5% when the true rate is ~98.75%.

A critical caveat for tournament contexts: with only ~67 games per tournament, isotonic regression can **overfit** if calibrated on tournament data alone. The recommended approach is calibrating on out-of-fold predictions across **10+ seasons of regular-season and tournament games** (~50,000+ games), as the Odds Gods system does. An arxiv paper on deep learning NCAA predictions (2508.02725v1) found that training with **Brier loss directly** (rather than binary cross-entropy) produced superior calibration from the start, potentially reducing the need for post-hoc calibration.

**Realistic expectations by base model type**:

| Base model | Typical uncalibrated Brier | Post-isotonic Brier | Relative improvement |
|---|---|---|---|
| Logistic regression | 0.190–0.210 | 0.185–0.200 | 2–5% |
| GBDTs (XGBoost/LightGBM) | 0.175–0.195 | 0.170–0.190 | 1–3% |
| Neural networks / SVMs | 0.200–0.250 | 0.180–0.210 | 10–20% |

---

## 7. WAB is essential for selection modeling but secondary for advancement prediction

Wins Above Bubble has become **the NCAA selection committee's most important metric** — Dan Gavitt (NCAA VP of Men's Basketball) stated in 2026 that at-large selection was "probably more highly correlated to a team's WAB ranking than it was their NET ranking." WAB was officially added to committee team sheets in 2024. The **WAB #40 line** has emerged as the de facto selection cutline: in 2025, all teams in the top 40 of WAB were selected.

However, WAB is fundamentally a **résumé metric, not a predictive metric**. It measures wins vs. what a bubble team would accumulate against the same schedule, but is **blind to margin of victory**. ESPN's Bubble Watch explicitly categorizes WAB as a résumé metric alongside SOR and NET, separate from predictive metrics (BPI, KenPom, Bart Torvik). Miami (Ohio) in 2026 illustrates the gap: 31-1 record, ~38th in WAB, but 87th in Bart Torvik and 93rd in KenPom.

**Recommended weighting**: For **selection/bubble prediction models**, WAB should carry **25–30%** weight. For **bracket advancement prediction**, WAB should carry **10–15%** weight — it captures a "proven winners" signal (ability to close out games under pressure) that pure efficiency metrics miss, but efficiency-based metrics like AdjEM are more robust game-level predictors. WAB's greatest bracket value is identifying teams whose records may be inflated by close-game luck versus those who have genuinely earned difficult wins.

---

## 8. The Big Ten's tournament underperformance has partially reversed

From 2000–2019, the Big Ten was actually the **best conference at exceeding seed expectations**, with +24.1 wins above seed expectation per Barttorvik PASE — nearly double any other conference. The severe underperformance narrative began in **2021–2022**: in 2021, the Big Ten sent 9 teams but saw #1 Illinois, #2 Ohio State, and #2 Iowa all eliminated early. FiveThirtyEight identified a 3-point shooting collapse as a contributing factor — Big Ten teams shot **27 fewer threes than expected** across 33 tournament games in 2021–2022.

By 2025, the pattern had **partially reversed at the early rounds but persisted in deep rounds**. The Big Ten went a historic **8-0 in the first round** (NCAA record), but only Michigan State survived past the Round of 32, with 7 of 8 teams eliminated by the Sweet 16. The conference's overall 13-8 record looked respectable but still underperformed given seeding quality. Most strikingly, the Big Ten has **not won a national championship since Michigan State in 2000** — a 25-year drought during which the Big East has won eight titles.

The **Big 12** has been the most consistent over-performer from 2021–2025, producing two national champions (Baylor 2021, Kansas 2022) and sending Houston to the 2025 Final Four. The **SEC** has surged dramatically, culminating in a historic 2025 season with a record 14 bids, a national champion (Florida), and all four #1 seeds in the Final Four. The **Mountain West** has been the most consistent under-performer among multi-bid conferences (0-4 in 2022, 2-4 in both 2024 and 2025). The **ACC** shows extreme year-to-year variance (4-7 in 2021, 11-2 in 2022) and defies consistent adjustment.

**Recommended conference adjustments for prediction models**:

| Conference | Adjustment | Magnitude |
|---|---|---|
| Big 12 | Positive | +1–2% win probability per round |
| SEC | Positive (trending up) | +1–3%, especially for higher seeds |
| Big Ten | Slight negative for deep rounds | -1–2% at Elite Eight+ |
| Big East | High variance; adjust by team quality | Neutral baseline |
| ACC | No consistent adjustment | High variance |
| Mountain West | Slight negative | -1–2% for non-top-team entries |

---

## Conclusion: where to focus model improvements

Three adjustments offer the highest expected return. First, **recalibrate seed-matchup priors** for the 68-team era — the 6-vs-11 line at ~52% for the 11-seed and the 8-vs-9 line at ~62% for the 9-seed are dramatic departures from all-time rates that many models still use. Second, **implement a structured fraud score** weighted heavily on offensive-defensive imbalance (25%) and KenPom-vs-seed deviation (25%), with luck as a 15% penalty modifier — this directly addresses the "paper tiger" problem that produces the splashiest bracket-busting upsets. Third, **shift from manual feature weights to gradient-boosted ensembles** of 5–8 diverse rating systems; the literature consistently shows that learned weights outperform fixed ones, and the marginal gain from isotonic calibration (0.005–0.015 Brier) is real but secondary to getting feature selection and model architecture right. The tempo signal should be incorporated as a *team-profile* characteristic (slower underdogs are more dangerous) rather than a game-level prediction, resolving the Berkeley-Harvard contradiction in favor of the more current and methodologically appropriate Toohey (2025) finding. Finally, conference adjustments should be applied modestly — the Big Ten deep-round penalty and Big 12/SEC bonuses are supported by 2021–2025 data, but year-to-year variance in conference performance is high enough that team-level metrics should always dominate.