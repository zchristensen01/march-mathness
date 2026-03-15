// Enhanced NCAA Tournament Team Ranking System
// Incorporating research on various predictive metrics for tournament success

// Define the conference strength weights (SEC highest at 1.00)
const conferenceWeights = {
    "SEC": 1.00,
    "Big Ten": 0.98,
    "Big 12": 0.96,
    "Big East": 0.93,
    "ACC": 0.92,
    "Atlantic 10": 0.90,
    "Mountain West": 0.88,
    "Ivy League": 0.87,
    "Conference USA": 0.86,
    "Southern": 0.85,
    "Missouri Valley": 0.84,
    "WCC": 0.84,
    "MAC": 0.84,
    "American": 0.83,
    "WAC": 0.83,
    "ASUN": 0.83,
    "Horizon League": 0.82,
    "America East": 0.81,
    "Big West": 0.80,
    "Summit League": 0.80,
    "Sun Belt": 0.79,
    "Big South": 0.78,
    "Coastal Athletic": 0.78,
    "Big Sky": 0.78,
    "Ohio Valley": 0.78,
    "Patriot League": 0.78,
    "Northeast": 0.77,
    "Southland": 0.77,
    "MAAC": 0.77,
    "SWAC": 0.76,
    "MEAC": 0.75
  };
  
  // 1. Championship Contender Index - based on profile of past champions
  // Emphasizes metrics that are common among tournament winners
  const championshipWeights = {
    // Core Efficiency Metrics (30% total)
    AdjEM: 0.12,             // Adjusted Efficiency Margin (12%)
    AdjO: 0.10,              // Adjusted Offensive Efficiency (10%)
    AdjD: 0.08,              // Adjusted Defensive Efficiency (8%)
    
    // Four Factors (25% total)
    Shooting: 0.10,          // Shooting metrics (10%) - eFG%, 3P%, 2P%
    Turnovers: 0.06,         // Turnover metrics (6%)
    Rebounding: 0.05,        // Rebounding metrics (5%)
    FreeThrows: 0.04,        // Free throw metrics (4%)
    
    // Schedule and Tournament Factors (20% total)
    SOS: 0.08,               // Strength of schedule (8%)
    EliteSOS: 0.06,          // Elite competition SOS (6%)
    Quad1Wins: 0.06,         // Quality wins against top competition (6%)
    
    // Team Composition Factors (15% total)
    StarPower: 0.06,         // Star player impact (6%)
    Experience: 0.05,        // Team experience (5%)
    Height: 0.04,            // Team height advantage (4%)
    BenchMinutes: 0.0001,    // Bench depth (minimal weight)
    
    // Momentum and Form (5% total)
    Momentum: 0.05,          // Recent performance (5%)
    Consistency: 0.0001,     // Consistency across ranking systems (minimal weight)
    
    // Stylistic Metrics (5% total)
    BallMovement: 0.02,      // Assist to turnover ratio (2%)
    DefensivePlaymaking: 0.02, // Block and steal percentages (2%)
    Tempo: 0.01,             // Pace of play (1%)
    
    // Advanced Metrics (5% total)
    Barthag: 0.03,           // Barthag power rating (3%)
    PPP: 0.02,               // Points per possession metrics (2%)
    ThreePointProfile: 0.0001  // Three-point attempt rate and defense (minimal weight)
  };
  
  // 2. Cinderella Potential - refined based on research
  // Emphasizes factors common among double-digit seeds that reach Sweet 16
  const cinderellaWeights = {
    // Core Efficiency Metrics (15% total)
    AdjEM: 0.04,
    AdjO: 0.08,              // Strong offense is key for Cinderellas (8%)
    AdjD: 0.03,              // At least average defense (3%)
    
    // Four Factors (40% total)
    Shooting: 0.18,          // Shooting metrics (18%) - eFG%, 3P%, 2P%
    Turnovers: 0.10,         // Turnover metrics (10%)
    Rebounding: 0.08,        // Rebounding metrics (8%) - critical for Cinderellas
    FreeThrows: 0.04,        // Free throw metrics (4%)
    
    // Schedule and Tournament Factors (10% total)
    SOS: 0.06,               // Strength of schedule (6%)
    EliteSOS: 0.02,
    Quad1Wins: 0.02,
    
    // Team Composition Factors (15% total)
    StarPower: 0.07,         // Star player impact (7%) - can take over games
    Experience: 0.04,        // Experience matters for upsets (4%)
    Height: 0.02,            // Team height advantage (2%)
    BenchMinutes: 0.02,      // Bench depth (2%)
    
    // Momentum and Form (10% total)
    Momentum: 0.10,          // Recent performance (10%)
    Consistency: 0.0001,
    
    // Stylistic Metrics (10% total)
    BallMovement: 0.05,      // Assist to turnover ratio (5%)
    DefensivePlaymaking: 0.03, // Block and steal percentages (3%)
    Tempo: 0.02,             // Pace of play (2%)
    
    // Three-Point Metrics (high emphasis based on research)
    ThreePointProfile: 0.10  // Three-point shooting important for Cinderellas
  };
  
  // 3. Defensive Domination - Teams that win with defense
  const defensiveWeights = {
    // Core Efficiency Metrics (30% total)
    AdjEM: 0.05,
    AdjO: 0.05,
    AdjD: 0.20,              // Adjusted Defensive Efficiency (20%)
    
    // Four Factors (35% total)
    Shooting: 0.05,          
    Turnovers: 0.10,         // Forcing turnovers (10%)
    Rebounding: 0.12,        // Defensive rebounding (12%)
    FreeThrows: 0.08,        // Avoiding fouls and free throws (8%)
    
    // Defensive Metrics (20% total)
    OpposingShooting: 0.12,  // Opponent eFG% (12%)
    DefensivePlaymaking: 0.08, // Block and steal percentages (8%)
    
    // Team Composition Factors (10% total)
    Height: 0.06,            // Team height advantage (6%)
    Experience: 0.02,        // Veteran defenders (2%)
    StarPower: 0.02,         // Defensive stoppers (2%)
    
    // Schedule Factors (5% total)
    SOS: 0.02,
    EliteSOS: 0.03,          // Performance against elite offenses (3%)
    
    // Physical Metrics
    Physicality: 0.08,       // Physical defensive metrics (8%)
    
    // Tempo and Style
    Tempo: 0.02,             // Usually slower pace is better for defense (negative correlation)
    BallMovement: 0.02,      // Limiting assists (2%)
    PPP: 0.03                // Points per possession allowed (3%)
  };
  
  // 4. Offensive Firepower - Teams with explosive scoring
  const offensiveWeights = {
    // Core Efficiency Metrics (35% total)
    AdjEM: 0.05,
    AdjO: 0.25,              // Adjusted Offensive Efficiency (25%)
    AdjD: 0.05,
    
    // Four Factors (35% total)
    Shooting: 0.18,          // Shooting metrics (18%) - eFG%
    Turnovers: 0.06,         // Low turnover rate (6%)
    Rebounding: 0.06,        // Offensive rebounding (6%)
    FreeThrows: 0.05,        // Free throw rate and % (5%)
    
    // Scoring Metrics (15% total)
    PPP: 0.08,               // Points per possession (8%)
    ThreePointProfile: 0.07, // Three-point shooting (7%)
    
    // Style and Pace (5% total)
    Tempo: 0.03,             // Faster pace (3%)
    BallMovement: 0.02,      // Ball movement (2%)
    
    // Team Composition (10% total)
    StarPower: 0.05,         // Scoring stars (5%)
    BenchMinutes: 0.02,      // Bench scoring (2%)
    Experience: 0.03,        // Experienced scorers (3%)
    
    // Schedule Factors
    Quad1Wins: 0.03,         // Success against good defenses (3%)
    SOS: 0.02                // Quality competition (2%)
  };
  
  // 5. Momentum Masters - Teams peaking at the right time
  const momentumWeights = {
    // Recent Performance (35% total)
    Momentum: 0.35,          // Performance in last 10 games (35%)
    
    // Quality Wins (25% total)
    Quad1Wins: 0.15,         // Recent quality wins (15%)
    EliteSOS: 0.10,          // Strong late-season schedule (10%)
    
    // Team Trajectory (20% total)
    OffensiveTrend: 0.10,    // Improving offensive metrics (10%)
    DefensiveTrend: 0.10,    // Improving defensive metrics (10%)
    
    // Team Composition (10% total)
    Experience: 0.04,        // Veteran leadership (4%)
    StarPower: 0.03,         // Star players getting hot (3%)
    Health: 0.03,            // Team getting healthier (3%)
    
    // Efficiency Metrics (10% total)
    AdjEM: 0.04,             // Overall team strength (4%)
    AdjO: 0.03,              // Offensive efficiency (3%)
    AdjD: 0.03,              // Defensive efficiency (3%)
    
    // Other Factors
    BallMovement: 0.01,      // Improving ball movement
    Turnovers: 0.02,         // Decreasing turnovers
    Shooting: 0.02           // Improving shooting
  };
  
  // 6. Giant Killers - Teams specifically built to upset higher seeds
  const giantKillerWeights = {
    // Three-Point Prowess (25% total)
    ThreePointProfile: 0.15, // Three-point volume (15%)
    Shooting: 0.10,          // Three-point accuracy (10%)
    
    // Defense and Disruption (25% total)
    Turnovers: 0.10,         // Forcing turnovers (10%)
    DefensivePlaymaking: 0.10, // Steals and blocks (10%)
    AdjD: 0.05,              // Defensive efficiency (5%)
    
    // Offensive Efficiency (15% total)
    AdjO: 0.10,              // Offensive efficiency (10%)
    PPP: 0.05,               // Points per possession (5%)
    
    // Experience and Coaching (15% total)
    Experience: 0.07,        // Veteran players (7%)
    StarPower: 0.05,         // Go-to players in clutch (5%)
    CoachingExperience: 0.03, // Tournament experience (3%)
    
    // Style Factors (10% total)
    Tempo: 0.05,             // Pace control (5%)
    BallMovement: 0.05,      // Ball movement (5%)
    
    // Free Throw Shooting (5% total)
    FreeThrows: 0.05,        // Free throw percentage (5%)
    
    // Resilience Factors (5% total)
    CloseGameMetric: 0.05,   // Performance in close games (5%)
  };
  
  // 7. Physical Dominance - Teams with size and physical advantages
  const physicalDominanceWeights = {
    // Size Metrics (40% total)
    Height: 0.20,            // Team height (20%)
    EffectiveHeight: 0.20,   // Functional size (20%)
    
    // Rebounding (25% total)
    Rebounding: 0.25,        // Combined rebounding metrics (25%)
    
    // Interior Scoring and Defense (20% total)
    InsideScoring: 0.10,     // Two-point scoring (10%)
    InteriorDefense: 0.10,   // Paint protection metrics (10%)
    
    // Physical Play Indicators (15% total)
    FreeThrows: 0.08,        // Free throw rate (8%)
    DefensivePlaymaking: 0.07 // Block percentage (7%)
  };
  
  // 8. Tournament Experience - Teams with veterans and tourney experience
  const tournamentExperienceWeights = {
    // Experience Metrics (50% total)
    Experience: 0.30,        // Team experience level (30%)
    TournamentHistory: 0.20, // Program tournament success (20%)
    
    // Coaching Factors (25% total)
    CoachExperience: 0.15,   // Coach tournament experience (15%)
    CoachSuccess: 0.10,      // Coach tournament wins (10%)
    
    // Clutch Performance (15% total)
    CloseGameMetric: 0.15,   // Performance in close games (15%)
    
    // Team Chemistry (10% total)
    BallMovement: 0.05,      // Assist metrics as chemistry indicator (5%)
    ReturnedMinutes: 0.05    // Continuity from previous season (5%)
  };
  
  // 9. Clutch Performance - Teams that excel in tight games
  const clutchPerformanceWeights = {
    // Close Game Metrics (35% total)
    CloseGameRecord: 0.20,   // Record in games decided by 5 points or less (20%)
    ClutchDefense: 0.15,     // Defensive rating in last 5 minutes of close games (15%)
    
    // Free Throw Metrics (20% total)
    FreeThrows: 0.15,        // Free throw percentage (15%)
    LateFTPercentage: 0.05,  // Free throw % in last 5 minutes (5%)
    
    // Turnover Control (15% total)
    Turnovers: 0.15,         // Low turnover rate in close games (15%)
    
    // Star Power (15% total)
    StarPower: 0.15,         // Go-to players in clutch (15%)
    
    // Experience Factors (15% total)
    Experience: 0.10,        // Team experience (10%)
    CoachClutchRecord: 0.05, // Coach record in close games (5%)
  };
  
  // 10. Balanced Excellence - Teams with no significant weaknesses
  const balancedExcellenceWeights = {
    // Efficiency Balance (35% total)
    AdjO: 0.18,              // Offensive efficiency (18%)
    AdjD: 0.17,              // Defensive efficiency (17%)
    
    // Four Factors Balance (30% total)
    Shooting: 0.08,          // Shooting efficiency (8%)
    Turnovers: 0.08,         // Turnover control (8%)
    Rebounding: 0.07,        // Rebounding metrics (7%)
    FreeThrows: 0.07,        // Free throw metrics (7%)
    
    // Team Composition (20% total)
    StarPower: 0.07,         // Star players (7%)
    BenchMinutes: 0.07,      // Bench contribution (7%)
    Experience: 0.06,        // Team experience (6%)
    
    // Schedule Strength (15% total)
    SOS: 0.08,               // Overall schedule (8%)
    Quad1Wins: 0.07          // Quality wins (7%)
  };
  
  const defaultWeights = {
    AdjEM: 0.25,
    AdjO: 0.15,
    AdjD: 0.15,
    Barthag: 0.05,
    Shooting: 0.08,
    Turnovers: 0.05,
    Rebounding: 0.05,
    FreeThrows: 0.03,
    SOS: 0.05,
    Quad1Wins: 0.04,
    StarPower: 0.03,
    Experience: 0.03,
    Momentum: 0.04
  };

  // Define specific weights for different attributes in each model
  const attributeWeights = {
    // Physical Dominance specific
    EffectiveHeight: {
      physicalDominanceWeights: 0.20
    },
    InsideScoring: {
      physicalDominanceWeights: 0.10,
      offensiveWeights: 0.05
    },
    InteriorDefense: {
      physicalDominanceWeights: 0.10,
      defensiveWeights: 0.08
    },
    
    // Clutch performance specific
    CloseGameRecord: {
      clutchPerformanceWeights: 0.20,
      tournamentExperienceWeights: 0.05
    },
    ClutchDefense: {
      clutchPerformanceWeights: 0.15
    },
    LateFTPercentage: {
      clutchPerformanceWeights: 0.05
    },
    
    // Tournament Experience specific
    TournamentHistory: {
      tournamentExperienceWeights: 0.20
    },
    CoachExperience: {
      tournamentExperienceWeights: 0.15,
      giantKillerWeights: 0.03
    },
    CoachSuccess: {
      tournamentExperienceWeights: 0.10
    },
    ReturnedMinutes: {
      tournamentExperienceWeights: 0.05
    },
    
    // Offensive specific
    OffensiveTrend: {
      momentumWeights: 0.10
    },
    
    // Defensive specific
    DefensiveTrend: {
      momentumWeights: 0.10
    },
    OpposingShooting: {
      defensiveWeights: 0.12
    },
    
    // Other specific attributes
    Health: {
      momentumWeights: 0.03
    },
    CoachClutchRecord: {
      clutchPerformanceWeights: 0.05
    },
    Physicality: {
      defensiveWeights: 0.08,
      physicalDominanceWeights: 0.05
    }
  };
  
  // Helper functions for normalization
  const normalizeValue = (value, min, max) => {
    if (value === undefined || isNaN(value)) return 0.5; // Default midpoint if data missing
    return Math.max(0, Math.min(1, (value - min) / (max - min)));
  };
  
  const normalizeInverse = (value, min, max) => {
    if (value === undefined || isNaN(value)) return 0.5; // Default midpoint if data missing
    return Math.max(0, Math.min(1, (max - value) / (max - min)));
  };
  /**
 * Apply attribute-specific weights to enhance specific team characteristics
 * @param {Object} team - Team data object
 * @param {Object} weights - Primary weights for the model (e.g. championshipWeights)
 * @param {Object} attributeWeightsForModel - Specific attribute weights for this model
 * @returns {Object} - Enhanced team data with attribute-adjusted scores
 */
function applyAttributeWeights(team, weights, attributeWeightsForModel) {
    if (!team || !weights || !attributeWeightsForModel) return team;
    
    // Create a deep copy of the team to avoid modifying the original
    const enhancedTeam = JSON.parse(JSON.stringify(team));
    
    // Get the appropriate attributeWeights for this specific model
    const modelType = getModelTypeFromWeights(weights);
    if (!modelType) return enhancedTeam;
    
    // Apply specific weights for this model type
    Object.entries(attributeWeights).forEach(([attribute, modelWeights]) => {
      const weight = modelWeights[modelType];
      if (weight && enhancedTeam[attribute] !== undefined) {
        enhancedTeam[attribute] = enhancedTeam[attribute] * weight;
      }
    });
    
    return enhancedTeam;
  }
  
  /**
   * Helper function to determine which model type is being used
   */
  function getModelTypeFromWeights(weights) {
    if (weights === championshipWeights) return 'championshipWeights';
    if (weights === cinderellaWeights) return 'cinderellaWeights';
    if (weights === defensiveWeights) return 'defensiveWeights';
    if (weights === offensiveWeights) return 'offensiveWeights';
    if (weights === momentumWeights) return 'momentumWeights';
    if (weights === giantKillerWeights) return 'giantKillerWeights';
    if (weights === physicalDominanceWeights) return 'physicalDominanceWeights';
    if (weights === tournamentExperienceWeights) return 'tournamentExperienceWeights';
    if (weights === clutchPerformanceWeights) return 'clutchPerformanceWeights';
    if (weights === balancedExcellenceWeights) return 'balancedExcellenceWeights';
    return null;
  }

  /**
   * Calculate composite score for a team using the provided weights
   */
  function calculateTeamScore(team, weights, attributeWeightsForModel = {}, applyConference = true) {
    // Add debugging check
    if (!team) {
        console.error("Team object is undefined in calculateTeamScore");
        return 0;
    }
    
    // Apply attribute weights first - add this line
    const enhancedTeam = applyAttributeWeights(team, weights, attributeWeightsForModel);
    
    // Continue with the rest of your function but use enhancedTeam instead of team
    
    // For example, change:
    if (enhancedTeam.AdjEM === undefined) {
        console.error(`Team ${enhancedTeam.Team || 'unknown'} is missing AdjEM field. Available fields: ${Object.keys(enhancedTeam).join(', ')}`);
        return 0;
    }
    
    if (!enhancedTeam) return 0;
    
    // Normalize values to 0-1 scale where 1 is best

    // Core Efficiency Metrics
    const adjEM = normalizeValue(parseFloat(enhancedTeam.AdjEM) || 0, -20, 40);
    const adjO = normalizeValue(parseFloat(enhancedTeam.AdjO) || 0, 95, 130);
    const adjD = normalizeInverse(parseFloat(enhancedTeam.AdjD) || 125, 80, 125);

    // Shooting metrics
    const eFG = normalizeValue(parseFloat(enhancedTeam["eFG%"]) || 0, 45, 60);
    const oppEFG = normalizeInverse(parseFloat(enhancedTeam["Opp_eFG%"]) || 60, 40, 60);
    const threeP = normalizeValue(parseFloat(enhancedTeam["3P%"]) || 0, 30, 40);
    const twoP = normalizeValue(parseFloat(enhancedTeam["2P%"]) || 0, 45, 60);
    const threePD = normalizeInverse(parseFloat(enhancedTeam["3P_%_D"]) || 40, 25, 40);
    const twoPD = normalizeInverse(parseFloat(enhancedTeam["2P_%_D"]) || 55, 40, 55);

    // Turnover metrics
    const to = normalizeInverse(parseFloat(enhancedTeam["TO%"]) || 25, 10, 25);
    const oppTO = normalizeValue(parseFloat(enhancedTeam["Opp_TO%"]) || 10, 10, 25);

    // Rebounding metrics
    const or = normalizeValue(parseFloat(enhancedTeam["OR%"]) || 0, 20, 40);
    const dr = normalizeValue(parseFloat(enhancedTeam["DR%"]) || 0, 65, 85);

    // Free throw metrics
    const ftr = normalizeValue(parseFloat(enhancedTeam.FTR) || 0, 20, 45);
    const oppFTR = normalizeInverse(parseFloat(enhancedTeam["Opp_FTR"]) || 45, 20, 45);
    const ftPct = normalizeValue(parseFloat(enhancedTeam["FT%"]) || 0, 65, 80);

    // Ball movement metrics
    const astTO = normalizeValue(parseFloat(enhancedTeam.AST_TO) || 0.8, 0.8, 2.1);
    const astPct = normalizeValue(parseFloat(enhancedTeam["Ast_%"]) || 40, 40, 65);
    const oppAstPct = normalizeInverse(parseFloat(enhancedTeam["Op_Ast_%"]) || 60, 35, 60);

    // Schedule metrics
    const sos = normalizeValue(parseFloat(enhancedTeam.SOS) || 350, 1, 350);
    const eliteSOS = normalizeValue(parseFloat(enhancedTeam.Elite_SOS) || 0, 0, 50);
    const quad1Wins = normalizeValue(parseFloat(enhancedTeam.Quad1_Wins) || 0, 0, 12);

    // Team composition metrics
    const starIndex = normalizeValue(parseFloat(enhancedTeam.Star_Player_Index) || 1, 1, 10);
    const benchMinutes = normalizeValue(parseFloat(enhancedTeam.Bench_Minutes_Pct) || 20, 20, 40);
    const experience = normalizeValue(parseFloat(enhancedTeam.Exp) || 0, 0, 3);

    // Height metrics
    const avgHeight = normalizeValue(parseFloat(enhancedTeam.Avg_Hgt) || 75, 75, 80);
    const effHeight = normalizeValue(parseFloat(enhancedTeam.Eff_Hgt) || 77, 77, 83);

    // Momentum and form metrics
    const lastTen = normalizeValue(parseFloat(enhancedTeam.Last_10_Games_Metric) || 0.40, 0.30, 1.0);

    // Consistency across ranking systems
    const kenPomRank = parseFloat(enhancedTeam.KenPom_Rank) || 100;
    const torvikRank = parseFloat(enhancedTeam.Torvik_Rank) || 100;
    const masseyRank = parseFloat(enhancedTeam.Massey_Rank) || 100;
    const netRank = parseFloat(enhancedTeam.NET_Rank) || 100;
    const avgRank = (kenPomRank + torvikRank + masseyRank + netRank) / 4;
    const consistencyRank = normalizeInverse(avgRank, 1, 350);

    // Barthag and other advanced metrics
    const barthag = normalizeValue(parseFloat(enhancedTeam.Barthag) || 0, 0.2, 1.0);
    const pppOff = normalizeValue(parseFloat(enhancedTeam.PPP_Off) || 0.8, 0.9, 1.25);
    const pppDef = normalizeInverse(parseFloat(enhancedTeam.PPP_Def) || 1.2, 0.8, 1.2);

    // Stylistic metrics
    const tempo = normalizeValue(parseFloat(enhancedTeam.Tempo) || 60, 60, 75);
    const rawT = normalizeValue(parseFloat(enhancedTeam.Raw_T) || 60, 60, 75);
    const adjT = normalizeValue(parseFloat(enhancedTeam.Adj_T) || 60, 60, 75);

    // Three-point profile
    const threeRate = normalizeValue(parseFloat(enhancedTeam["3P_Rate"]) || 25, 25, 50);
    const threeRateD = normalizeInverse(parseFloat(enhancedTeam["3P_Rate_D"]) || 50, 30, 50);

    // Defensive playmaking
    const blkPct = normalizeValue(parseFloat(enhancedTeam["Blk_%"]) || 5, 5, 20);
    const blkedPct = normalizeInverse(parseFloat(enhancedTeam["Blked_%"]) || 15, 5, 15);

    // Record metrics
    const recordParts = enhancedTeam.Record ? enhancedTeam.Record.split('-') : ['0', '0'];
    const wins = parseFloat(recordParts[0]) || parseFloat(enhancedTeam.Wins) || 0;
    const losses = parseFloat(recordParts[1]) || 0;
    const games = wins + losses || parseFloat(enhancedTeam.Games) || 30;
    const winPct = normalizeValue(wins / games, 0.4, 0.95);
        
    // Derived metrics based on research (these would normally come from additional data)
    // Close game performance (approximating from available data)
    const closeGamePerformance = (lastTen + winPct + 0.5 * ftPct + 0.5 * to) / 3;
    
    // Three-point consistency (approximating)
    const threePtConsistency = (threeP + 0.7 * threeRate) / 1.7;
    
    // Tournament history (approximating from team quality metrics)
    const tournamentHistory = (barthag + 0.5 * experience + 0.5 * consistencyRank) / 2;
    
    // Coach experience (approximating)
    const coachExperience = (experience + tournamentHistory) / 2;
    
    // Physical play metrics
    const physicality = (or + blkPct + ftr + 0.5 * effHeight) / 3.5;
    
    // Inside scoring capability
    const insideScoring = (twoP + or + 0.5 * ftr) / 2.5;
    
    // Interior defense capability
    const interiorDefense = (twoPD + blkPct + dr) / 3;
    
    // Calculate the weighted components
    let score = 0;
    
    // Core Efficiency Metrics
    score += (weights.AdjEM || 0) * adjEM;
    score += (weights.AdjO || 0) * adjO;
    score += (weights.AdjD || 0) * adjD;
    
    // Shooting component - specialized by model type
    let shootingScore;
    if (weights === cinderellaWeights || weights === giantKillerWeights) {
      // For Cinderella predictor, emphasize 3P shooting more
      shootingScore = (eFG * 0.2) + (oppEFG * 0.2) + (threeP * 0.3) + (twoP * 0.1) + 
                      (threePD * 0.1) + (twoPD * 0.1);
    } 
    else if (weights === defensiveWeights) {
      // For defensive teams, emphasize opponent shooting stats
      shootingScore = (eFG * 0.1) + (oppEFG * 0.4) + (threeP * 0.05) + (twoP * 0.05) + 
                      (threePD * 0.2) + (twoPD * 0.2);
    }
    else if (weights === offensiveWeights) {
      // For offensive teams, emphasize offensive shooting stats
      shootingScore = (eFG * 0.4) + (oppEFG * 0.05) + (threeP * 0.3) + (twoP * 0.2) + 
                      (threePD * 0.025) + (twoPD * 0.025);
    }
    else if (weights === championshipWeights) {
      // For championship contenders, balance offense and defense
      shootingScore = (eFG * 0.3) + (oppEFG * 0.3) + (threeP * 0.15) + (twoP * 0.15) + 
                     (threePD * 0.05) + (twoPD * 0.05);
    }
    else {
      // Default balanced approach
      shootingScore = (eFG * 0.25) + (oppEFG * 0.25) + (threeP * 0.125) + (twoP * 0.125) + 
                      (threePD * 0.125) + (twoPD * 0.125);
    }
    score += (weights.Shooting || 0) * shootingScore;
    
    // Turnover component - specialized by model type
    let turnoverScore;
    if (weights === cinderellaWeights || weights === giantKillerWeights || weights === defensiveWeights) {
      turnoverScore = (to * 0.3) + (oppTO * 0.7);  // Emphasize forcing turnovers
    }
    else if (weights === offensiveWeights || weights === clutchPerformanceWeights) {
      turnoverScore = (to * 0.7) + (oppTO * 0.3);  // Emphasize ball security
    }
    else {
      turnoverScore = (to * 0.5) + (oppTO * 0.5);  // Balanced approach
    }
    score += (weights.Turnovers || 0) * turnoverScore;
    
    // Rebounding component - specialized by model type
    let reboundingScore;
    if (weights === offensiveWeights) {
      reboundingScore = (or * 0.8) + (dr * 0.2);  // Offensive emphasis
    } 
    else if (weights === defensiveWeights) {
      reboundingScore = (or * 0.2) + (dr * 0.8);  // Defensive emphasis
    } 
    else if (weights === physicalDominanceWeights) {
      reboundingScore = (or * 0.5) + (dr * 0.5) + (effHeight * 0.2);  // Size+rebounding
    } 
    else {
      reboundingScore = (or * 0.5) + (dr * 0.5);  // Balanced
    }
    score += (weights.Rebounding || 0) * reboundingScore;
    
    // Free throw component - specialized by model type
    let freeThrowScore;
    if (weights === giantKillerWeights || weights === clutchPerformanceWeights) {
      freeThrowScore = (ftr * 0.2) + (oppFTR * 0.2) + (ftPct * 0.6);  // FT% emphasis
    } 
    else if (weights === defensiveWeights) {
      freeThrowScore = (ftr * 0.2) + (oppFTR * 0.7) + (ftPct * 0.1);  // Opponent FTR emphasis
    } 
    else {
      freeThrowScore = (ftr * 0.35) + (oppFTR * 0.35) + (ftPct * 0.3);  // Balanced
    }
    score += (weights.FreeThrows || 0) * freeThrowScore;
    
    // Ball movement component
    const ballMovementScore = (astTO * 0.5) + (astPct * 0.3) + (oppAstPct * 0.2);
    score += (weights.BallMovement || 0) * ballMovementScore;
    
    // Schedule components
    score += (weights.SOS || 0) * sos;
    score += (weights.EliteSOS || 0) * eliteSOS;
    score += (weights.Quad1Wins || 0) * quad1Wins;
    
    // Team composition components
    score += (weights.StarPower || 0) * starIndex;
    score += (weights.BenchMinutes || 0) * benchMinutes;
    score += (weights.Experience || 0) * experience;
    
    // Height component
    const heightScore = (avgHeight * 0.4) + (effHeight * 0.6);
    score += (weights.Height || 0) * heightScore;
    
    // Momentum component
    score += (weights.Momentum || 0) * lastTen;
    
    // Consistency component
    score += (weights.Consistency || 0) * consistencyRank;
    
    // Barthag component
    score += (weights.Barthag || 0) * barthag;
    
    // PPP component
    let pppScore;
    if (weights === offensiveWeights) {
      pppScore = pppOff;  // Offensive emphasis
    } 
    else if (weights === defensiveWeights) {
      pppScore = pppDef;  // Defensive emphasis
    } 
    else {
      pppScore = (pppOff * 0.6) + (pppDef * 0.4);  // Balanced with slight offensive emphasis
    }
    score += (weights.PPP || 0) * pppScore;
    
    // Tempo component
    let tempoScore;
    if (weights === defensiveWeights) {
      // For defensive teams, slower tempo is often better
      tempoScore = 1 - ((tempo * 0.5) + (rawT * 0.25) + (adjT * 0.25));
    } 
    else if (weights === offensiveWeights) {
      // For offensive teams, faster tempo often helps
      tempoScore = (tempo * 0.5) + (rawT * 0.25) + (adjT * 0.25);
    }
    else {
      // For other models, use the tempo that fits team's style
      tempoScore = 0.5 + (((tempo * 0.5) + (rawT * 0.25) + (adjT * 0.25)) - 0.5) * 0.8;
    }
    score += (weights.Tempo || 0) * tempoScore;
    
    // Three-point profile component
    const threePointScore = (threeRate * 0.6) + (threeRateD * 0.4);
    score += (weights.ThreePointProfile || 0) * threePointScore;
    
    // Defensive playmaking component
    const defensivePlaymakingScore = (blkPct * 0.6) + (blkedPct * 0.4);
    score += (weights.DefensivePlaymaking || 0) * defensivePlaymakingScore;
    
    // Add model-specific attribute weights
    if (attributeWeightsForModel.OpposingShooting) {
      score += attributeWeightsForModel.OpposingShooting * oppEFG;
    }
    
    if (attributeWeightsForModel.EffectiveHeight) {
      score += attributeWeightsForModel.EffectiveHeight * effHeight;
    }
    
    if (attributeWeightsForModel.InsideScoring) {
      score += attributeWeightsForModel.InsideScoring * insideScoring;
    }
    
    if (attributeWeightsForModel.InteriorDefense) {
      score += attributeWeightsForModel.InteriorDefense * interiorDefense;
    }
    
    if (attributeWeightsForModel.CloseGameRecord) {
      score += attributeWeightsForModel.CloseGameRecord * closeGamePerformance;
    }
    
    if (attributeWeightsForModel.ClutchDefense) {
      // Approximate: Good defensive teams tend to be clutch
      score += attributeWeightsForModel.ClutchDefense * ((adjD * 0.6) + (blkPct * 0.2) + (dr * 0.2));
    }
    
    if (attributeWeightsForModel.LateFTPercentage) {
      // We use regular FT% as approximation
      score += attributeWeightsForModel.LateFTPercentage * ftPct;
    }
    
    if (attributeWeightsForModel.TournamentHistory) {
      score += attributeWeightsForModel.TournamentHistory * tournamentHistory;
    }
    
    if (attributeWeightsForModel.CoachExperience) {
      score += attributeWeightsForModel.CoachExperience * coachExperience;
    }
    
    if (attributeWeightsForModel.OffensiveTrend) {
      // Approximating with last 10 games performance
      score += attributeWeightsForModel.OffensiveTrend * lastTen;
    }
    
    if (attributeWeightsForModel.DefensiveTrend) {
      // Approximating with last 10 games performance
      score += attributeWeightsForModel.DefensiveTrend * lastTen;
    }
    
    if (attributeWeightsForModel.Physicality) {
      score += attributeWeightsForModel.Physicality * physicality;
    }

    // Scale to 0-100
  score = score * 100;
  
  // Apply conference strength adjustment if requested
  if (applyConference) {
    const confWeight = conferenceWeights[team.Conference] || 1.0;
    score = score * confWeight;
  }
  
  return Math.round(score * 10) / 10; // Round to 1 decimal place
}

// Function to calculate all model scores for a team
function calculateAllModelScores(team) {
  return {
    championshipScore: calculateTeamScore(team, championshipWeights),
    cinderellaScore: calculateTeamScore(team, cinderellaWeights),
    defensiveScore: calculateTeamScore(team, defensiveWeights),
    offensiveScore: calculateTeamScore(team, offensiveWeights),
    momentumScore: calculateTeamScore(team, momentumWeights),
    giantKillerScore: calculateTeamScore(team, giantKillerWeights),
    physicalScore: calculateTeamScore(team, physicalDominanceWeights),
    experienceScore: calculateTeamScore(team, tournamentExperienceWeights),
    clutchScore: calculateTeamScore(team, clutchPerformanceWeights),
    balancedScore: calculateTeamScore(team, balancedExcellenceWeights)
  };
}

/**
 * Process CSV data into an array of team objects
 */
function processCSV(csvText) {
    const lines = csvText.trim().split('\n');
    const headers = lines[0].split(',');
    
    const teams = [];
    for (let i = 1; i < lines.length; i++) {
      // Handle CSV parsing more robustly, accounting for quoted fields with commas
      const values = parseCSVLine(lines[i], headers.length);
      
      const team = {};
      headers.forEach((header, index) => {
        let value = values[index];
        // Clean up the value
        if (value !== undefined) {
          value = value.trim();
          // Convert numeric strings to numbers if appropriate
          if (!isNaN(value) && value !== '') {
            value = Number(value);
          }
        } else {
          value = '';
        }
        team[header] = value;
      });
      
      // Inspect and fix the team data
      const fixedTeam = inspectAndFixTeam(team);
      teams.push(fixedTeam);
    }
    
    // Add logging to help diagnose issues
    console.log(`Processed ${teams.length} teams from CSV`);
    console.log(`First team fields: ${Object.keys(teams[0]).slice(0, 10).join(', ')}`);
    
    return teams;
  }

  // Function to inspect and fix team data
function inspectAndFixTeam(team) {
    // Make a copy
    const fixedTeam = {...team};
    
    // Check for AdjEM, AdjO, AdjD and map them from Adj OE, Adj DE if needed
    if (team["Adj OE"] !== undefined && !team.AdjO) {
      fixedTeam.AdjO = parseFloat(team["Adj OE"]);
    }
    
    if (team["Adj DE"] !== undefined && !team.AdjD) {
      fixedTeam.AdjD = parseFloat(team["Adj DE"]);
    }
    
    // Calculate AdjEM from AdjO and AdjD if it doesn't exist
    if (!fixedTeam.AdjEM && fixedTeam.AdjO && fixedTeam.AdjD) {
      fixedTeam.AdjEM = fixedTeam.AdjO - fixedTeam.AdjD;
    }
    
    // Map other field names that might be different
    const fieldMappings = {
      "eFG": "eFG%",
      "eFG D.": "Opp_eFG%",
      "TOV%": "TO%",
      "TOV% D": "Opp_TO%", 
      "O Reb%": "OR%",
      "Op OReb%": "Opp_OR%",
      "FT Rate": "FTR",
      "FT Rate D": "Opp_FTR",
      "Ast %": "Ast_%",
      "Op Ast %": "Op_Ast_%",
      "3P %": "3P%",
      "2P %": "2P%",
      "3P % D.": "3P_%_D",
      "2P % D.": "2P_%_D",
      "Blk %": "Blk_%",
      "Blked %": "Blked_%",
      "3P Rate": "3P_Rate",
      "3P Rate D": "3P_Rate_D",
      "Raw T": "Raw_T",
      "Adj. T": "Adj_T",
      "PPP Off.": "PPP_Off",
      "PPP Def.": "PPP_Def",
      "Elite SOS": "Elite_SOS",
      "Avg Hgt.": "Avg_Hgt",
      "Eff. Hgt.": "Eff_Hgt",
      "Exp.": "Exp"
    };
    
    // Apply mappings
    Object.entries(fieldMappings).forEach(([csvField, expectedField]) => {
      if (team[csvField] !== undefined && !team[expectedField]) {
        fixedTeam[expectedField] = parseFloat(team[csvField]) || team[csvField];
      }
    });
    
    // Add missing derived values
    if (!fixedTeam["DR%"] && fixedTeam["Opp_OR%"]) {
      fixedTeam["DR%"] = 100 - parseFloat(fixedTeam["Opp_OR%"]);
    }
    
    // Fill in default values for important missing fields
    const defaultValues = {
      "Seed": fixedTeam.Seed || "10",
      "Conference": fixedTeam.Conference || "Unknown",
      "Star_Player_Index": fixedTeam.Star_Player_Index || 5 + Math.random() * 5,
      "Bench_Minutes_Pct": fixedTeam.Bench_Minutes_Pct || 20 + Math.random() * 20,
      "Last_10_Games_Metric": fixedTeam.Last_10_Games_Metric || 0.5 + Math.random() * 0.5
    };
    
    Object.entries(defaultValues).forEach(([field, value]) => {
      if (!fixedTeam[field]) {
        fixedTeam[field] = value;
      }
    });
    
    return fixedTeam;
  }

// Run specific analysis types
function runAnalysis(analysisType, teams, attributeWeightsParam) {
    switch (analysisType) {
      case 'championship':
        return recalculateScores(teams, championshipWeights, attributeWeightsParam);
      case 'cinderella':
        return recalculateScores(teams, cinderellaWeights, attributeWeightsParam);
      case 'defensive':
        return recalculateScores(teams, defensiveWeights, attributeWeightsParam);
      case 'offensive':
        return recalculateScores(teams, offensiveWeights, attributeWeightsParam);
      case 'momentum':
        return recalculateScores(teams, momentumWeights, attributeWeightsParam);
      case 'giantkiller':
        return recalculateScores(teams, giantKillerWeights, attributeWeightsParam);
      case 'physical':
        return recalculateScores(teams, physicalDominanceWeights, attributeWeightsParam);
      case 'experience':
        return recalculateScores(teams, tournamentExperienceWeights, attributeWeightsParam);
      case 'clutch':
        return recalculateScores(teams, clutchPerformanceWeights, attributeWeightsParam);
      case 'balanced':
        return recalculateScores(teams, balancedExcellenceWeights, attributeWeightsParam);
      case 'upset':
        return identifyUpsetPotential(teams, attributeWeightsParam || defaultWeights);
      case 'final4':
        return predictFinalFour(teams, attributeWeightsParam || defaultWeights);
      default:
        return recalculateScores(teams, defaultWeights, attributeWeightsParam);
    }
  }

// Recalculate scores for all teams using provided weights
function recalculateScores(teams, weights, attributeWeightsParam, applyConference = true) {
    if (!weights) {
      console.error("Weights parameter is undefined in recalculateScores");
      weights = defaultWeights; // Fallback to default
    }
    
    return teams.map(team => {
      if (!team) {
        console.error("Encountered undefined team in recalculateScores");
        return null; // Skip this team or return a placeholder
      }
      
      const newTeam = {...team};
      // Pass the attributeWeightsParam to calculateTeamScore
      newTeam.Calculated_Score = calculateTeamScore(team, weights, attributeWeightsParam, applyConference);
      return newTeam;
    }).filter(team => team !== null).sort((a, b) => b.Calculated_Score - a.Calculated_Score);
  }

/**
 * Generate CSV string from team objects
 */
function generateCSV(teams, headers) {
    let csv = headers.join(',') + '\n';
    
    teams.forEach(team => {
      const row = headers.map(header => {
        const value = team[header] !== undefined ? team[header] : '';
        // Quote values with commas
        return typeof value === 'string' && value.includes(',') ? `"${value}"` : value;
      }).join(',');
      csv += row + '\n';
    });
    
    return csv;
  }
  
  /**
   * Parse a CSV line properly, handling quoted fields with commas
   */
  function parseCSVLine(line, expectedLength) {
    const values = [];
    let inQuotes = false;
    let currentValue = '';
    
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      
      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        values.push(currentValue);
        currentValue = '';
      } else {
        currentValue += char;
      }
    }
    
    // Add the last value
    values.push(currentValue);
    
    // Ensure we have the expected number of values
    while (values.length < expectedLength) {
      values.push('');
    }
    
    return values;
  }
  
  /**
   * Identify potential Cinderella teams (double-digit seeds with high scores)
   */
  function identifyCinderellas(teams) {
    return teams
      .filter(team => parseInt(team.Seed) >= 8) // Double-digit seeds
      .filter(team => {
        // Calculate over-performance vs seed expectation
        const seedExpectation = 100 - ((parseInt(team.Seed) - 1) * 6);
        const overperformance = team.Calculated_Score - seedExpectation;
        
        return overperformance > 5; // Significantly outperforming seed
      })
      .sort((a, b) => b.Calculated_Score - a.Calculated_Score)
      .slice(0, 10); // Top 5 candidates
  }
  
  /**
   * Get team strengths for Cinderella analysis
   */
  function getTeamStrengths(team) {
    const strengths = [];
    
    // Shooting strengths
    if (parseFloat(team["3P%"]) > 36) strengths.push("excellent 3-point shooting");
    if (parseFloat(team["eFG%"]) > 55) strengths.push("efficient shooting");
    if (parseFloat(team["Opp_eFG%"]) < 46) strengths.push("strong defensive field goal percentage");
    
    // Possession strengths
    if (parseFloat(team["TO%"]) < 15) strengths.push("takes care of the ball");
    if (parseFloat(team["Opp_TO%"]) > 20) strengths.push("creates lots of turnovers");
    if (parseFloat(team.AST_TO) > 1.5) strengths.push("excellent ball movement");
    
    // Free throw strengths
    if (parseFloat(team["FT%"]) > 75) strengths.push("strong free throw shooting");
    
    // Form strengths
    if (parseFloat(team.Last_10_Games_Metric) > 0.8) strengths.push("excellent recent form");
    
    // Star power
    if (parseFloat(team.Star_Player_Index) >= 8) strengths.push("star player who can take over games");
    
    // Rebounding strengths
    if (parseFloat(team["DR%"]) > 75) strengths.push("elite defensive rebounding");
    if (parseFloat(team["OR%"]) > 35) strengths.push("dominant offensive rebounding");
    
    // Advanced metrics
    if (parseFloat(team.Barthag) > 0.92) strengths.push("strong power rating");
    if (parseFloat(team.Tempo) > 70) strengths.push("plays at a fast pace");
    if (parseFloat(team["Blk_%"]) > 13) strengths.push("elite shot blocking");
    
    // Record strength
    const recordParts = team.Record ? team.Record.split('-') : ['0', '0'];
    const wins = parseFloat(recordParts[0]) || parseFloat(team.Wins) || 0;
    const losses = parseFloat(recordParts[1]) || 0;
    if (wins / (wins + losses) > 0.75) strengths.push("excellent win percentage");
    
    // Quality wins
    if (parseFloat(team.Quad1_Wins) >= 5) strengths.push("proven against top competition");
    
    // Height advantage
    if (parseFloat(team.Eff_Hgt) > 81) strengths.push("significant height advantage");
    
    // Experience
    if (parseFloat(team.Exp) > 2.3) strengths.push("veteran team with experience");
    
    return strengths;
  }
  
  /**
   * Identify potential first-round upsets
   */
  function identifyUpsetPotential(teams, weights) {
    // Define regions and matchups
    const regions = {
      "East": [
        { seeds: [1, 16], teams: ["Auburn", "Saint Francis"] },
        { seeds: [8, 9], teams: ["Louisville", "Creighton"] },
        { seeds: [5, 12], teams: ["Michigan", "UC San Diego"] },
        { seeds: [4, 13], teams: ["Texas A&M", "Yale"] },
        { seeds: [6, 11], teams: ["Mississippi", "North Carolina"] },
        { seeds: [3, 14], teams: ["Iowa St.", "Lipscomb"] },
        { seeds: [7, 10], teams: ["Marquette", "New Mexico"] },
        { seeds: [2, 15], teams: ["Michigan St.", "Bryant"] }
      ],
      "South": [
        { seeds: [1, 16], teams: ["Florida", "Norfolk St."] },
        { seeds: [8, 9], teams: ["Connecticut", "Oklahoma"] },
        { seeds: [5, 12], teams: ["Memphis", "Colorado St."] },
        { seeds: [4, 13], teams: ["Maryland", "Grand Canyon"] },
        { seeds: [6, 11], teams: ["Missouri", "Drake"] },
        { seeds: [3, 14], teams: ["Texas Tech", "UNC Wilmington"] },
        { seeds: [7, 10], teams: ["Kansas", "Arkansas"] },
        { seeds: [2, 15], teams: ["St. John's", "Omaha"] }
      ],
      "West": [
        { seeds: [1, 16], teams: ["Duke", "American"] },
        { seeds: [8, 9], teams: ["Mississippi St.", "Baylor"] },
        { seeds: [5, 12], teams: ["Oregon", "Liberty"] },
        { seeds: [4, 13], teams: ["Arizona", "Akron"] },
        { seeds: [6, 11], teams: ["BYU", "VCU"] },
        { seeds: [3, 14], teams: ["Wisconsin", "Montana"] },
        { seeds: [7, 10], teams: ["Saint Mary's", "Vanderbilt"] },
        { seeds: [2, 15], teams: ["Alabama", "Robert Morris"] }
      ],
      "Midwest": [
        { seeds: [1, 16], teams: ["Houston", "SIU Edwardsville"] },
        { seeds: [8, 9], teams: ["Gonzaga", "Georgia"] },
        { seeds: [5, 12], teams: ["Clemson", "McNeese"] },
        { seeds: [4, 13], teams: ["Purdue", "High Point"] },
        { seeds: [6, 11], teams: ["Illinois", "Texas"] },
        { seeds: [3, 14], teams: ["Kentucky", "Troy"] },
        { seeds: [7, 10], teams: ["UCLA", "Utah St."] },
        { seeds: [2, 15], teams: ["Tennessee", "Wofford"] }
      ]
    };
  
    // Calculate scores for all teams
    const rankedTeams = recalculateScores(teams, weights || defaultWeights);
    
    // Create a map of team names to team objects
    const teamMap = {};
    rankedTeams.forEach(team => {
      teamMap[team.Team] = team;
    });
    
    // Potential upsets are where lower seed (higher number) beats higher seed (lower number)
    const potentialUpsets = [];
    
    // Analyze each region's matchups
    Object.entries(regions).forEach(([regionName, matchups]) => {
      matchups.forEach(matchup => {
        const [higherSeed, lowerSeed] = matchup.seeds;
        const [favoriteTeamName, underdogTeamName] = matchup.teams;
        
        // Find the team objects
        const favorite = teamMap[favoriteTeamName];
        const underdog = teamMap[underdogTeamName];
        
        // Skip if we don't have both teams
        if (!favorite || !underdog) {
          console.log(`Could not find teams for matchup: ${favoriteTeamName} vs ${underdogTeamName}`);
          return;
        }
        
        // Calculate upset potential (underdog score / favorite score)
        const upsetPotential = underdog.Calculated_Score / favorite.Calculated_Score;
        
        // If upset potential exceeds threshold, add to list
        // Adjust threshold based on seed difference
        let threshold = 0.85;
        if (higherSeed === 8 && lowerSeed === 9) threshold = 0.95; // 8-9 games are essentially toss-ups
        if (higherSeed === 7 && lowerSeed === 10) threshold = 0.90; // 7-10 games often see upsets
        if (higherSeed === 1 || higherSeed === 2) threshold = 0.75; // 1-16, 2-15 upsets are very rare
        
        if (upsetPotential > threshold) {
          potentialUpsets.push({
            ...underdog,
            region: regionName,
            opponent: favorite.Team,
            opponentSeed: favorite.Seed,
            opponentScore: favorite.Calculated_Score,
            upsetPotential: upsetPotential.toFixed(2),
            matchup: `${lowerSeed} ${underdogTeamName} vs ${higherSeed} ${favoriteTeamName}`,
            underdogName: underdogTeamName,
            favoriteName: favoriteTeamName,
            underdogSeed: underdog.Seed,
            favoriteSeed: favorite.Seed,
            underdogStrengths: getTeamStrengths(underdog),
            matchupAdvantage: []
          });
        }
      });
    });
    
    // Sort by upset potential
    return potentialUpsets.sort((a, b) => b.upsetPotential - a.upsetPotential).slice(0, 5);
  }
  
  /**
   * Predict Final Four teams
   */
  function predictFinalFour(teams, weights) {
    // Calculate scores for all teams
    const rankedTeams = recalculateScores(teams, weights || defaultWeights);
    
    // Get top 4 teams across all regions
    const finalFour = rankedTeams.slice(0, 4).map((team, index) => {
      return {
        region: ['East', 'West', 'South', 'Midwest'][index],
        team: team,  // This should be the full team object
        strengths: getTeamStrengths(team)
      };
    });
    
    return finalFour;
  }

// Export functions for use in other modules
module.exports = {
    conferenceWeights,
    championshipWeights,
    cinderellaWeights,
    defensiveWeights,
    offensiveWeights,
    momentumWeights,
    giantKillerWeights,
    physicalDominanceWeights,
    tournamentExperienceWeights,
    clutchPerformanceWeights,
    balancedExcellenceWeights,
    inspectAndFixTeam,
    calculateTeamScore,
    calculateAllModelScores,
    processCSV,
    runAnalysis,
    recalculateScores,
    defaultWeights,
    generateCSV,
    identifyUpsetPotential,
    predictFinalFour,
    identifyCinderellas,
    getTeamStrengths,
    attributeWeights: {
      cinderellaWeights: cinderellaWeights,
      giantKillerWeights: giantKillerWeights,
      defensiveWeights: defensiveWeights,
      offensiveWeights: offensiveWeights,
      momentumWeights: momentumWeights,
      physicalDominanceWeights: physicalDominanceWeights,
      tournamentExperienceWeights: tournamentExperienceWeights,
      clutchPerformanceWeights: clutchPerformanceWeights,
      balancedExcellenceWeights: balancedExcellenceWeights
    }
  };