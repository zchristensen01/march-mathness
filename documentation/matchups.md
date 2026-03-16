# Predicting college basketball matchups: the stats that actually matter

**Adjusted efficiency margin (AdjEM) is the single most predictive statistic for college basketball game outcomes**, and every validated model—KenPom, BartTorvik, ESPN BPI, LRMC—builds from it as the foundation. The Four Factors of basketball (Dean Oliver) explain **98% of the variance in offensive efficiency** but add almost zero independent predictive power once AdjEM is incorporated, because they are its component parts. The optimal mathematical approach uses either a normal CDF or logistic function to convert an expected point differential into win probability, with a game-level standard deviation of **~10–11 points**. Soft factors like coaching experience and program prestige are largely captured within efficiency metrics already, though roster experience, star player quality, and preseason priors add modest incremental value. Three-point shooting randomness is the primary engine of March Madness upsets—and it is fundamentally unpredictable.

---

## Efficiency margin dominates all other predictors

Every serious college basketball model centers on adjusted efficiency margin—the difference between a team's points scored and points allowed per 100 possessions, adjusted for opponent strength and game location. KenPom's AdjEM, BartTorvik's equivalent, and ESPN BPI's core rating all express this same concept. Over **22 seasons of KenPom data**, only two national champions ranked outside the top 20 in both offensive and defensive efficiency. The LRMC model (Kvam & Sokol, 2006, published in *Naval Research Logistics*) demonstrated that efficiency-based ratings significantly outperform tournament seedings, the AP Poll, RPI, and Sagarin ratings for predicting NCAA tournament outcomes.

The key formulas for head-to-head prediction follow a two-step process. First, calculate expected point differential:

**Expected Point Diff = (AdjEM_A − AdjEM_B) × Expected Possessions / 100**

Where expected possessions = **(AdjT_A × AdjT_B) / National Average Tempo**. Second, convert that differential into win probability using a normal distribution with **σ ≈ 11 points** (KenPom's current method):

**Win% = Φ(Point Diff / 11)**

This produces intuitive results: a **5-point expected margin ≈ 68% win probability**, a **10-point margin ≈ 82%**, and a **15-point margin ≈ 91%**. Each point of game-level advantage translates to roughly **3–3.5 percentage points** of win probability near the center of the distribution. BartTorvik uses an alternative approach—calculating Barthag (Pythagorean win expectation with exponent **11.5**) and then applying the **Log5 formula**: P(A beats B) = (pA − pA×pB) / (pA + pB − 2×pA×pB).

When running LASSO logistic regression with all available features (Hill, 2022), the model retains **Barthag, seed differential, AdjOE, AdjDE, eFG%, and FTR**—notably dropping TOV% and ORB% as redundant once efficiency metrics are included. This confirms that AdjEM captures the vast majority of predictive information, with only shooting efficiency and free throw rate providing marginal additional signal.

---

## Dean Oliver's Four Factors: diagnostic power, not additive prediction

Oliver's original weights from *Basketball on Paper* (2004) assigned shooting (eFG%) **40%**, turnovers (TOV%) **25%**, rebounding (ORB%) **20%**, and free throws (FTR) **15%**. Multiple independent regression analyses have since validated the ranking but shifted the weights. Justin Jacobs (Squared2020, 2017) found weights of approximately **46/35/12/7** using NBA data with R² = 0.91. Statathlon's 2017 analysis found **43/39/10/8**. The consistent finding: Oliver was right about the hierarchy, but shooting and turnovers deserve **~80% combined weight** while rebounding and free throws deserve only **~20%**.

Ed Feng (The Power Rank) confirmed these four factors explain **98% of offensive efficiency variance** in college basketball—an extraordinarily high figure. However, Jordan Sperber's critical 2013 study tested whether matchup-level four factor differentials (e.g., Team A's eFG% vs. Team B's opponent eFG%) improve prediction beyond adjusted efficiency alone. His finding was definitive: **matchup-level four factor analysis adds zero meaningful predictive power** beyond what AdjEM already captures. Even in extreme matchup scenarios (top/bottom 10% in each factor), prediction error was less than 1 point per 100 possessions.

This means the Four Factors are best understood as **diagnostic tools**—they explain *why* a team's efficiency is what it is (great shooting? elite turnover avoidance?) rather than serving as independent prediction inputs. For a matchup model, including the raw four factor differentials alongside AdjEM introduces multicollinearity without improving accuracy. That said, if your model does not already use AdjEM, the four factors with revised weights (~45/35/12/8) are an excellent proxy for building efficiency from scratch.

---

## How tempo shapes the matchup calculation

Tempo is a **style descriptor and score multiplier, not a quality indicator**. Virginia won the 2019 national championship while ranking dead last in tempo. What matters is efficiency per possession; tempo determines how many possessions occur, which scales the absolute margin.

KenPom's expected tempo formula is multiplicative, not a simple average:

**Expected Possessions = (TeamA_AdjT / National Avg) × (TeamB_AdjT / National Avg) × National Avg**

This design has an important consequence. A team averaging 62 possessions per game is already being "pulled faster" by opponents who prefer higher tempos—so its true preferred pace is even slower than 62. When two slow teams meet, the formula produces a tempo **slower than either team's season average**, correctly reflecting that both teams' averages were inflated by faster opponents. The game plays closer to the slower team's preference than a simple average would suggest.

For prediction purposes, **tempo affects expected total score but not win probability meaningfully**—with one critical exception. Slower games produce fewer possessions, which compresses the margin and **increases variance relative to the spread**. This means slow-tempo matchups slightly favor upsets. A team with a 10-point AdjEM advantage at 65 possessions has a 6.5-point expected margin; at 75 possessions, that becomes 7.5 points. The difference is modest but real. When building a model, tempo should be used to scale the AdjEM differential to get the expected game-level point spread before converting to probability.

---

## Recency, momentum, and the limits of "hot streaks"

BartTorvik applies explicit recency weighting: games in the **last 40 days count 100%**, degrading 1% per day to a floor of **60% for games 80+ days old**. KenPom also weights recent games more heavily, though his specific formula is proprietary. Both approaches reflect a reasonable belief that teams change over a season—players improve, rotations solidify, injuries heal.

The scientific evidence on momentum is more nuanced than casual fans assume. The original "hot hand fallacy" research (Gilovich, Tversky & Vallone, 1985) concluded streaks were cognitive illusions. Miller & Sanjurjo's 2017 reanalysis found a statistical bias in the original study, revealing a **real but small** hot hand effect: roughly **+2.7% shooting probability after 2 consecutive makes**, rising to **+5.8% after 4 makes**, found in only a subset of players. Team-level momentum research remains inconclusive, with academic reviews showing conclusions split roughly 50-50.

The practical implication: late-season improvement backed by **genuine efficiency gains** (improved AdjEM, not just wins against weak opponents) is predictive. Winning streaks against low-quality competition or conference tournament runs without corresponding efficiency improvement should be **heavily discounted**. BartTorvik's 40-day window represents a reasonable compromise. For your model, a **Last_10_Games_Metric** is useful if it measures efficiency change rather than just wins, but it should receive substantially less weight than full-season adjusted metrics. A reasonable approach: weight recent form at **5–10%** of total model input, with full-season efficiency carrying **60–70%**.

---

## Soft factors contribute less than most people think

**Coaching experience** correlates with tournament success—7 of the last 10 non-outlier champions had coaches with **24+ years of experience and 500+ career wins**. But this is largely a selection effect: great coaches recruit great players, making it nearly impossible to isolate a pure "coaching bump." No rigorous peer-reviewed study has quantified an exact win probability bonus per tournament appearance. Coach experience is best treated as a **tiebreaker-level factor** (1–3% weight), not a primary predictor.

**Program prestige** is almost entirely captured by efficiency metrics. Duke, Kansas, and Kentucky rank highly in KenPom *because* they recruit elite talent, not because of mystical brand power. However, Nate Silver's FiveThirtyEight model found that the **preseason AP Poll adds genuine predictive value** beyond current-season efficiency—it captures crowd wisdom about talent and coaching quality that takes 30+ games to fully manifest in statistics. Ed Feng documented a remarkable finding: over 40 years, **zero teams** starting outside the preseason AP top 25 that earned a 1 or 2 seed made the Final Four (probability of this occurring by chance: ~1 in 7,500). This suggests preseason expectations capture something real about ceiling/talent that mid-season numbers miss.

**Star player quality** matters significantly. Evan Miya's research shows every top-10 end-of-season team had a player ranked in the **preseason top 100**, and 28 of 30 had a top-50 player. Player-level models (Miya's Bayesian Performance Rating) add predictive value beyond team-level efficiency, particularly for projecting roster changes and transfer impacts. **Roster experience** is consistently predictive: mid-major March Madness teams averaged **1.99 years of D1 experience** vs. 1.66 for non-tournament teams, and 18 of 25 mid-major tournament winners since 2022 gave **≥50% of minutes to returning players**.

**Bench depth** (Bench_Minutes_Pct) has mixed evidence. Quality of bench players matters more than depth itself. However, in the tournament's compressed timeline (6 games in ~3 weeks), thin rotations create vulnerability to foul trouble and fatigue, particularly in later rounds.

---

## The anatomy of March Madness upsets

Three-point shooting variance is the **primary mechanism driving upsets**, but it is fundamentally unpredictable. The Power Rank's analysis found that when 6+ point underdogs won, they shot **5.5% better than their season 3PT average** while favorites shot **5.5% worse**—a combined 7-point swing. KenPom's landmark study "The 3-Point Line is a Lottery" found **no correlation** in team 3PT% from early to late season, for offense or defense. Defenses have essentially no control once a three-point shot goes up. This randomness means that identifying *which specific* upsets will occur is structurally impossible—models can only identify elevated upset probability.

The University of Illinois BOSS method (Jacobson, Sauppe & Dutta, published in *JQAS*) analyzed 115 statistics and identified the **effective possession ratio** (possessions + offensive rebounds − turnovers / possessions), number of regular-season games played, and scoring chances per game as the most influential upset predictors. The Furman University model achieved **76% accuracy** on tournament games with ≥5 seed gap by combining 18 sub-models.

Several factors identify upset-prone favorites and dangerous underdogs:

- **Mis-seeded teams** where KenPom rank significantly differs from seed (e.g., a 7-seed ranked 18th in KenPom is overseeded and vulnerable)
- **High "Luck" rating** indicates a team won more close games than efficiency predicts—regression is expected
- **Slow-tempo matchups** compress margins and increase variance, favoring underdogs
- **Experienced underdogs with strong defense** are the most dangerous lower seeds
- **Three-point-dependent teams** are inherently volatile (both for upsets and for causing them), though research shows shooting *more* threes doesn't actually increase point variance—the binomial nature of basketball already ensures σ ≈ 7.5 points per team regardless of shot selection

---

## Optimal weighting framework for your model

Based on the synthesis of academic research, validated models, and analytical literature, here is a recommended importance hierarchy for the statistics available in your system:

| Tier | Stats | Approximate Weight | Rationale |
|------|-------|-------------------|-----------|
| **Tier 1: Foundation** | AdjEM (or AdjO + AdjD), Barthag | **50–60%** | Single most predictive factor; all models build from here |
| **Tier 2: Composite validation** | CompRank, Torvik_Rank, NET_Rank | **10–15%** | Ensemble of ratings outperforms any single system; provides robustness |
| **Tier 3: Shooting/Four Factors** | eFG%, Opp_eFG%, 3P%, 2P% (and defensive equivalents) | **5–10%** | Marginal signal beyond AdjEM; eFG% differential most valuable |
| **Tier 4: Experience/Talent** | Exp, Star_Player_Index | **5–8%** | Validated by Miya's research; captures roster quality beyond team stats |
| **Tier 5: Schedule strength** | SOS, Elite_SOS, Quad1_Wins, WAB | **3–5%** | Already mostly captured in adjusted metrics; Elite_SOS adds marginal value |
| **Tier 6: Recency/Form** | Last_10_Games_Metric, RankTrajectory | **3–5%** | Real but small signal; efficiency-based recent form > win/loss record |
| **Tier 7: Regression indicators** | Luck | **2–3%** | High luck → regression candidate; negative luck → undervalued |
| **Tier 8: Soft factors** | Coach_Tourney_Experience, Program_Prestige | **1–3%** | Largely captured elsewhere; useful as tiebreakers |
| **Tier 9: Style/Context** | Adj_T, 3P_Rate, Bench_Minutes_Pct, FTR, TO%, OR% | **1–3%** | Tempo scales margins; other factors mostly redundant with AdjEM |

For the mathematical implementation, **logistic regression on efficiency differential** remains the gold standard—competitive with or superior to complex machine learning approaches (Yuan et al., 2014; Kvam & Sokol, 2006). The recommended formula mirrors KenPom's current approach: calculate expected point differential from AdjEM and tempo, then convert via Φ(diff/σ) with σ ≈ 11. For neutral-site games (all NCAA tournament matchups), no home court adjustment is needed.

---

## Conclusion: what the research tells us to build

The research converges on several non-obvious insights. First, **simplicity wins**: a model using only AdjEM differential, scaled by expected tempo, and converted through a normal CDF captures the vast majority of predictive power. Adding dozens of features creates noise without meaningful accuracy gains. Second, the Four Factors are diagnostic—they tell you *why* a team is efficient, not *whether* it will win beyond what efficiency already reveals. Third, the most exploitable edges come from **identifying mis-seeded teams** (where the gap between seed and efficiency ranking is large) and **fading lucky teams** (whose records exceed their underlying quality). Fourth, three-point variance makes specific upset prediction structurally impossible; the best strategy is calibrated probability assignment, not upset-picking. Fifth, preseason priors and roster experience add real information that pure in-season efficiency misses—teams that look great statistically but lack top-end talent and experience systematically underperform in March. The optimal model is not the most complex one; it is the one that weights the right inputs correctly and respects the inherent ~10-point standard deviation of randomness that no model can eliminate.