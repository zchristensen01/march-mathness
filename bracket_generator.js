// Enhanced NCAA Tournament Bracket Generator
// Incorporates research insights on various team profiles and tournament success patterns

const fs = require('fs');
const enhancedRankingSystem = require('./enhanced_ranking_system.js');

/**
 * Generate multiple brackets with different strategies
 */
async function generateBrackets() {
  try {
    // Load team data using Node.js fs module
    const csvData = fs.readFileSync('final_table.csv', 'utf8');
    const rawTeams = enhancedRankingSystem.processCSV(csvData);
    
    // Process the team data
    const teams = processTeamData(rawTeams);
    console.log(`Loaded and processed ${teams.length} teams from CSV`);
    
    // Create new modified weight systems based on research
    const modifiedWeights = createModifiedWeightSystems();
    
    // Generate bracket options
    const brackets = {
      // Standard bracket - balanced approach
      standard: simulateBracket(teams, {
        championshipWeight: 0.5,
        clutchWeight: 0.2,
        balancedWeight: 0.2,
        momentumWeight: 0.1,
        upsetThreshold: 0.65
      }),
      
      // Favorites bracket - heavy focus on championship contender metrics
      favorites: simulateBracket(teams, {
        championshipWeight: 0.7,
        balancedWeight: 0.2,
        defensiveWeight: 0.1,
        upsetThreshold: 0.8 // Very few upsets
      }),
      
      // Upset special - more focus on giant killers and cinderellas
      // Enhanced to incorporate turnover forcing and three-point shooting success
      upsets: simulateBracket(teams, {
        championshipWeight: 0.1,  // Reduced from original
        giantKillerWeight: 0.4,   // Increased from original
        cinderellaWeight: 0.3,    // Increased
        momentumWeight: 0.2,
        upsetThreshold: 0.35      // Reduced to allow more upsets
      }, enhancedRankingSystem.attributeWeights.giantKillerWeights),
      
      // Analytics-driven - pure numbers approach
      analytics: simulateBracket(teams, {
        championshipWeight: 0.35,
        balancedWeight: 0.35,     // Higher weight on balanced teams
        adjOWeight: 0.15,         // Added weight for offensive efficiency
        adjDWeight: 0.15,         // Added weight for defensive efficiency
        upsetThreshold: 0.55
      }),
      
      // Cinderella focus - specifically for finding cinderella teams
      // Emphasizes three-point shooting, experience, and turnover creation
      cinderella: simulateBracket(teams, {
        championshipWeight: 0.1,  // Reduced from original
        cinderellaWeight: 0.5,    // Increased from original
        giantKillerWeight: 0.3, 
        momentumWeight: 0.1,
        upsetThreshold: 0.4
      }, enhancedRankingSystem.attributeWeights.cinderellaWeights),
      
      // Physical dominance - teams that win with size and strength
      // Added emphasis on rebounding and interior defense
      physical: simulateBracket(teams, {
        championshipWeight: 0.2,  // Reduced from original
        physicalWeight: 0.5,      // Increased from original
        defensiveWeight: 0.2,
        clutchWeight: 0.1,
        upsetThreshold: 0.55
      }, enhancedRankingSystem.attributeWeights.physicalDominanceWeights),
      
      // Momentum-based - teams that are hot coming into the tournament
      // Increased weight on recent performance
      momentum: simulateBracket(teams, {
        championshipWeight: 0.1,  // Reduced from original
        momentumWeight: 0.6,      // Increased from original
        clutchWeight: 0.2,
        adjOWeight: 0.1,          // Added for balance
        upsetThreshold: 0.45      // Reduced to allow more upsets
      }, enhancedRankingSystem.attributeWeights.momentumWeights),
      
      // Experience-based - veteran teams and coaches
      // Heavily weights experience factors
      experience: simulateBracket(teams, {
        championshipWeight: 0.2,   // Reduced from original
        experienceWeight: 0.6,     // Increased from original
        clutchWeight: 0.2,
        upsetThreshold: 0.55
      }, enhancedRankingSystem.attributeWeights.tournamentExperienceWeights)
    };
    
    // Generate bracket summary
    const summary = generateBracketSummary(brackets, teams);
    
    return {
      brackets,
      summary,
      teamMap: createTeamMap(teams)
    };
  } catch (error) {
    console.error("Error generating brackets:", error);
    return { error: error.message };
  }
}

/**
 * Create modified weight systems based on research insights
 */
function createModifiedWeightSystems() {
  // Modified Championship Contender Model
  // Based on research showing championship teams often excel in both offense and defense
  const enhancedChampionshipWeights = { 
    ...enhancedRankingSystem.championshipWeights 
  };
  enhancedChampionshipWeights.AdjO += 0.05; // Increased emphasis on offensive efficiency
  enhancedChampionshipWeights.AdjD += 0.05; // Increased emphasis on defensive efficiency
  enhancedChampionshipWeights.Experience += 0.03; // More emphasis on experience

  // Modified Cinderella Model
  // Based on research showing cinderellas often have good 3pt shooting and force turnovers
  const enhancedCinderellaWeights = { 
    ...enhancedRankingSystem.cinderellaWeights 
  };
  enhancedCinderellaWeights.ThreePointProfile += 0.08; // More emphasis on 3pt shooting
  enhancedCinderellaWeights.Turnovers += 0.05; // More emphasis on creating turnovers
  enhancedCinderellaWeights.Experience += 0.04; // More emphasis on experience
  
  // Modified Giant Killer Model
  // Based on research showing that giant-killers often create turnovers and shoot threes
  const enhancedGiantKillerWeights = { 
    ...enhancedRankingSystem.giantKillerWeights 
  };
  enhancedGiantKillerWeights.Turnovers += 0.05; // More emphasis on creating turnovers
  enhancedGiantKillerWeights.ThreePointProfile += 0.05; // More emphasis on 3pt shooting
  
  return {
    enhancedChampionshipWeights,
    enhancedCinderellaWeights,
    enhancedGiantKillerWeights
  };
}

/**
 * Process team data to ensure compatibility with ranking system
 */
function processTeamData(rawTeams) {
  return rawTeams.map((team, index) => {
    // Map fields from the CSV to what the ranking system expects
    const processedTeam = {
      ...team,
      // Use the rank/index as Seed if not provided (for demonstration)
      Seed: team.Seed || String(index + 1),
      // Map Adj OE and Adj DE to AdjO and AdjD
      AdjO: parseFloat(team["Adj OE"] || team.AdjO || 0),
      AdjD: parseFloat(team["Adj DE"] || team.AdjD || 0),
      // Calculate AdjEM from AdjO - AdjD if not provided
      AdjEM: parseFloat(team.AdjEM || (team["Adj OE"] - team["Adj DE"]) || 0),
      // Map shooting percentages
      "eFG%": parseFloat(team.eFG || team["eFG%"] || 0),
      "Opp_eFG%": parseFloat(team["eFG D."] || team["Opp_eFG%"] || 0),
      "3P%": parseFloat(team["3P %"] || team["3P%"] || 0),
      "2P%": parseFloat(team["2P %"] || team["2P%"] || 0),
      "3P_%_D": parseFloat(team["3P % D."] || team["3P_%_D"] || 0),
      "2P_%_D": parseFloat(team["2P % D."] || team["2P_%_D"] || 0),
      // Map turnover percentages
      "TO%": parseFloat(team["TOV%"] || team["TO%"] || 0),
      "Opp_TO%": parseFloat(team["TOV% D"] || team["Opp_TO%"] || 0),
      // Map rebounding percentages
      "OR%": parseFloat(team["O Reb%"] || team["OR%"] || 0),
      "DR%": 100 - parseFloat(team["Op OReb%"] || 0), // DR% is 100% - opponent's OR%
      // Map free throw rates
      FTR: parseFloat(team["FT Rate"] || team.FTR || 0),
      "Opp_FTR": parseFloat(team["FT Rate D"] || team["Opp_FTR"] || 0),
      "FT%": parseFloat(team["FT%"] || 0),
      // Map assist percentages
      "Ast_%": parseFloat(team["Ast %"] || team["Ast_%"] || 0),
      "Op_Ast_%": parseFloat(team["Op Ast %"] || team["Op_Ast_%"] || 0),
      // Map tempo stats
      Tempo: parseFloat(team["Raw T"] || team.Tempo || 0),
      Raw_T: parseFloat(team["Raw T"] || team.Raw_T || 0),
      Adj_T: parseFloat(team["Adj. T"] || team.Adj_T || 0),
      // Map block percentages
      "Blk_%": parseFloat(team["Blk %"] || team["Blk_%"] || 0),
      "Blked_%": parseFloat(team["Blked %"] || team["Blked_%"] || 0),
      // Map 3-point rates
      "3P_Rate": parseFloat(team["3P Rate"] || team["3P_Rate"] || 0),
      "3P_Rate_D": parseFloat(team["3P Rate D"] || team["3P_Rate_D"] || 0),
      // Map other needed stats
      Exp: parseFloat(team["Exp."] || team.Exp || 0),
      Elite_SOS: parseFloat(team["Elite SOS"] || team.Elite_SOS || 0),
      PPP_Off: parseFloat(team["PPP Off."] || team.PPP_Off || 0),
      PPP_Def: parseFloat(team["PPP Def."] || team.PPP_Def || 0),
      
      // Add derived or default fields that are needed but might not be in the CSV
      AST_TO: team.AST_TO || 1.0, // Default value if not available
      Star_Player_Index: team.Star_Player_Index || (Math.random() * 5 + 5), // Random value between 5-10
      Bench_Minutes_Pct: team.Bench_Minutes_Pct || 25, // Default bench minutes
      Last_10_Games_Metric: team.Last_10_Games_Metric || (Math.random() * 0.3 + 0.6), // Random value between 0.6-0.9
      
      // Conference is needed for conference strength adjustments
      Conference: team.Conference || "Unknown",
      
      // Parse record if available
      Record: team.Record || "0-0",
      
      // Height metrics
      Avg_Hgt: parseFloat(team["Avg Hgt."] || team.Avg_Hgt || 0),
      Eff_Hgt: parseFloat(team["Eff. Hgt."] || team.Eff_Hgt || 0)
    };
    
    return processedTeam;
  });
}

/**
 * Create a map of teams for quick lookup
 */
function createTeamMap(teams) {
  const teamMap = {};
  teams.forEach(team => {
    teamMap[team.Team] = team;
  });
  return teamMap;
}

/**
 * Simulate a bracket with a specific strategy
 * @param {Array} teams - Array of team objects
 * @param {Object} weights - Weight configuration for the simulation
 * @param {Object} attributeWeights - Optional attribute-specific weights
 */
function simulateBracket(teams, weights, attributeWeights = {}) {
  // Calculate team scores based on weight strategy
  const teamMap = {};
  teams.forEach(team => {
    const scores = calculateAllModelScores(team, attributeWeights);
    
    // Calculate weighted score based on strategy
    let weightedScore = 0;
    if (weights.championshipWeight) weightedScore += scores.championshipScore * weights.championshipWeight;
    if (weights.clutchWeight) weightedScore += scores.clutchScore * weights.clutchWeight;
    if (weights.balancedWeight) weightedScore += scores.balancedScore * weights.balancedWeight;
    if (weights.momentumWeight) weightedScore += scores.momentumScore * weights.momentumWeight;
    if (weights.cinderellaWeight) weightedScore += scores.cinderellaScore * weights.cinderellaWeight;
    if (weights.giantKillerWeight) weightedScore += scores.giantKillerScore * weights.giantKillerWeight;
    if (weights.defensiveWeight) weightedScore += scores.defensiveScore * weights.defensiveWeight;
    if (weights.offensiveWeight) weightedScore += scores.offensiveScore * weights.offensiveWeight;
    if (weights.physicalWeight) weightedScore += scores.physicalScore * weights.physicalWeight;
    if (weights.experienceWeight) weightedScore += scores.experienceScore * weights.experienceWeight;
    if (weights.adjOWeight) weightedScore += (team.AdjO - 100) / 30 * 100 * weights.adjOWeight;
    if (weights.adjDWeight) weightedScore += (100 - team.AdjD) / 20 * 100 * weights.adjDWeight;
    
    // Store in map for fast access
    teamMap[team.Team] = {
      ...team,
      scores,
      weightedScore
    };
  });
  
  // Define regions and matchups (based on actual bracket)
  const regions = {
    "East": [
      { round: "First", matchup: ["1", "16"], teams: ["Houston", "Saint Francis"] },
      { round: "First", matchup: ["8", "9"], teams: ["Louisville", "Creighton"] },
      { round: "First", matchup: ["5", "12"], teams: ["Michigan", "UC San Diego"] },
      { round: "First", matchup: ["4", "13"], teams: ["Texas A&M", "Yale"] },
      { round: "First", matchup: ["6", "11"], teams: ["Mississippi", "North Carolina"] },
      { round: "First", matchup: ["3", "14"], teams: ["Iowa St.", "Lipscomb"] },
      { round: "First", matchup: ["7", "10"], teams: ["Marquette", "New Mexico"] },
      { round: "First", matchup: ["2", "15"], teams: ["Michigan St.", "Bryant"] }
    ],
    "South": [
      { round: "First", matchup: ["1", "16"], teams: ["Florida", "Norfolk St."] },
      { round: "First", matchup: ["8", "9"], teams: ["Connecticut", "Oklahoma"] },
      { round: "First", matchup: ["5", "12"], teams: ["Memphis", "Colorado St."] },
      { round: "First", matchup: ["4", "13"], teams: ["Maryland", "Grand Canyon"] },
      { round: "First", matchup: ["6", "11"], teams: ["Missouri", "Drake"] },
      { round: "First", matchup: ["3", "14"], teams: ["Texas Tech", "UNC Wilmington"] },
      { round: "First", matchup: ["7", "10"], teams: ["Kansas", "Arkansas"] },
      { round: "First", matchup: ["2", "15"], teams: ["St. John's", "Omaha"] }
    ],
    "West": [
      { round: "First", matchup: ["1", "16"], teams: ["Duke", "American"] },
      { round: "First", matchup: ["8", "9"], teams: ["Mississippi St.", "Baylor"] },
      { round: "First", matchup: ["5", "12"], teams: ["Oregon", "Liberty"] },
      { round: "First", matchup: ["4", "13"], teams: ["Arizona", "Akron"] },
      { round: "First", matchup: ["6", "11"], teams: ["BYU", "VCU"] },
      { round: "First", matchup: ["3", "14"], teams: ["Wisconsin", "Montana"] },
      { round: "First", matchup: ["7", "10"], teams: ["Saint Mary's", "Vanderbilt"] },
      { round: "First", matchup: ["2", "15"], teams: ["Alabama", "Robert Morris"] }
    ],
    "Midwest": [
      { round: "First", matchup: ["1", "16"], teams: ["Auburn", "SIU Edwardsville"] },
      { round: "First", matchup: ["8", "9"], teams: ["Gonzaga", "Georgia"] },
      { round: "First", matchup: ["5", "12"], teams: ["Clemson", "McNeese"] },
      { round: "First", matchup: ["4", "13"], teams: ["Purdue", "High Point"] },
      { round: "First", matchup: ["6", "11"], teams: ["Illinois", "Texas"] },
      { round: "First", matchup: ["3", "14"], teams: ["Kentucky", "Troy"] },
      { round: "First", matchup: ["7", "10"], teams: ["UCLA", "Utah St."] },
      { round: "First", matchup: ["2", "15"], teams: ["Tennessee", "Wofford"] }
    ]
  };
  
  // Process each region
  const results = {};
  Object.keys(regions).forEach(region => {
    results[region] = simulateRegion(regions[region], teamMap, weights.upsetThreshold);
  });
  
  // Simulate Final Four
  const finalFour = {
    semifinals: [
      {
        teams: [results.East.winner, results.West.winner],
        winner: simulateMatchup(
          teamMap[results.East.winner], 
          teamMap[results.West.winner], 
          weights.upsetThreshold
        )
      },
      {
        teams: [results.South.winner, results.Midwest.winner],
        winner: simulateMatchup(
          teamMap[results.South.winner], 
          teamMap[results.Midwest.winner], 
          weights.upsetThreshold
        )
      }
    ]
  };
  
  // Championship game
  const championship = {
    teams: [finalFour.semifinals[0].winner, finalFour.semifinals[1].winner],
    winner: simulateMatchup(
      teamMap[finalFour.semifinals[0].winner],
      teamMap[finalFour.semifinals[1].winner],
      weights.upsetThreshold
    )
  };
  
  return {
    regions: results,
    finalFour,
    championship,
    champion: championship.winner,
    weights,
    teamMap
  };
}

/**
 * Simulate a single region
 */
function simulateRegion(regionMatchups, teamMap, upsetThreshold) {
  // Extract first round matchups
  const firstRound = regionMatchups.filter(m => m.round === "First");
  
  // Simulate first round (Round of 64)
  const roundOf32 = firstRound.map(matchup => {
    const team1 = teamMap[matchup.teams[0]];
    const team2 = teamMap[matchup.teams[1]];
    
    if (!team1 || !team2) {
      // Handle if a team doesn't exist in our dataset
      const missingTeam = !team1 ? matchup.teams[0] : matchup.teams[1];
      console.warn(`Team not found in dataset: ${missingTeam}`);
      
      // Return the team that does exist, or default to first team if both are missing
      return { 
        matchup: [matchup.teams[0], matchup.teams[1]],
        winner: team1 ? team1.Team : (team2 ? team2.Team : matchup.teams[0])
      };
    }
    
    // Override team seeds for simulation based on the matchup definition
    team1.Seed = matchup.matchup[0];
    team2.Seed = matchup.matchup[1];
    
    return {
      matchup: [team1.Team, team2.Team],
      winner: simulateMatchup(team1, team2, upsetThreshold)
    };
  });
  
  // Simulate Round of 32
  const sweet16 = [];
  for (let i = 0; i < roundOf32.length; i += 2) {
    const team1 = teamMap[roundOf32[i].winner];
    const team2 = teamMap[roundOf32[i+1].winner];
    
    sweet16.push({
      matchup: [roundOf32[i].winner, roundOf32[i+1].winner],
      winner: simulateMatchup(team1, team2, upsetThreshold)
    });
  }
  
  // Simulate Sweet 16
  const elite8 = [];
  for (let i = 0; i < sweet16.length; i += 2) {
    const team1 = teamMap[sweet16[i].winner];
    const team2 = teamMap[sweet16[i+1].winner];
    
    elite8.push({
      matchup: [sweet16[i].winner, sweet16[i+1].winner],
      winner: simulateMatchup(team1, team2, upsetThreshold)
    });
  }
  
  // Final Four representative
  const finalFour = {
    matchup: [elite8[0].winner, elite8[1].winner],
    winner: simulateMatchup(teamMap[elite8[0].winner], teamMap[elite8[1].winner], upsetThreshold)
  };
  
  return {
    roundOf32,
    sweet16,
    elite8,
    finalFour: [finalFour],
    winner: finalFour.winner
  };
}

/**
 * Simulate a matchup between two teams
 * Enhanced to incorporate research insights on upsets
 */
function simulateMatchup(team1, team2, upsetThreshold) {
  if (!team1 || !team2) {
    return team1 ? team1.Team : (team2 ? team2.Team : "Unknown");
  }
  
  // Get team seeds as numbers
  const seed1 = parseInt(team1.Seed);
  const seed2 = parseInt(team2.Seed);
  
  // Determine favorite and underdog
  const favorite = seed1 < seed2 ? team1 : team2;
  const underdog = seed1 < seed2 ? team2 : team1;
  
  // Calculate win probability based on weighted scores
  let favoriteWinProb = favorite.weightedScore / (favorite.weightedScore + underdog.weightedScore);
  
  // Adjust for seed differential
  const seedDiff = Math.abs(seed1 - seed2);
  let seedAdjustment = Math.min(0.15, seedDiff * 0.01); // Max 15% adjustment
  
  // For 8-9, 7-10 matchups, reduce the adjustment
  let adjustedFavoriteWinProb = 
    (Math.abs(seed1 - seed2) <= 2) ? 
    favoriteWinProb : 
    favoriteWinProb + seedAdjustment;
  
  // Apply specific factors known to influence upsets (based on research)
  // Turnovers - teams that win turnover battles have better upset chances
  if (parseFloat(underdog["Opp_TO%"]) > 22 && parseFloat(favorite["TO%"]) > 18) {
    adjustedFavoriteWinProb -= 0.05; // 5% less likely for favorite to win
  }
  
  // Three-point shooting - high volume three-point shooting teams have better upset chances
  if (parseFloat(underdog["3P%"]) > 37 && parseFloat(underdog["3P_Rate"]) > 40) {
    adjustedFavoriteWinProb -= 0.05; // 5% less likely for favorite to win
  }
  
  // Experience - veteran teams with tournament experience have better upset chances
  if (parseFloat(underdog.Exp) > 2.3 && parseFloat(favorite.Exp) < 1.8) {
    adjustedFavoriteWinProb -= 0.03; // 3% less likely for favorite to win
  }
  
  // Determine if an upset occurs
  const upsetOccurs = (1 - adjustedFavoriteWinProb) > upsetThreshold;
  
  // Determine winner
  if (upsetOccurs && (underdog.Seed !== "16" || favorite.Seed !== "1")) { // 16 seeds almost never beat 1 seeds
    return underdog.Team;
  }
  
  return favorite.Team;
}

/**
 * Calculate all model scores for a team
 */
function calculateAllModelScores(team, attributeWeights = {}) {
  // Calculate scores based on different ranking models
  // These values are used to weight teams for different bracket strategies
  return {
    championshipScore: enhancedRankingSystem.calculateTeamScore(team, enhancedRankingSystem.championshipWeights, attributeWeights.championshipWeights || {}),
    defensiveScore: enhancedRankingSystem.calculateTeamScore(team, enhancedRankingSystem.defensiveWeights, attributeWeights.defensiveWeights || {}),
    offensiveScore: enhancedRankingSystem.calculateTeamScore(team, enhancedRankingSystem.offensiveWeights, attributeWeights.offensiveWeights || {}),
    momentumScore: enhancedRankingSystem.calculateTeamScore(team, enhancedRankingSystem.momentumWeights, attributeWeights.momentumWeights || {}),
    giantKillerScore: enhancedRankingSystem.calculateTeamScore(team, enhancedRankingSystem.giantKillerWeights, attributeWeights.giantKillerWeights || {}),
    cinderellaScore: enhancedRankingSystem.calculateTeamScore(team, enhancedRankingSystem.cinderellaWeights, attributeWeights.cinderellaWeights || {}),
    physicalScore: team.physicalScore || enhancedRankingSystem.calculateTeamScore(team, enhancedRankingSystem.physicalDominanceWeights, attributeWeights.physicalDominanceWeights || {}),
    experienceScore: team.experienceScore || enhancedRankingSystem.calculateTeamScore(team, enhancedRankingSystem.tournamentExperienceWeights, attributeWeights.tournamentExperienceWeights || {}),
    clutchScore: team.clutchScore || enhancedRankingSystem.calculateTeamScore(team, enhancedRankingSystem.clutchPerformanceWeights, attributeWeights.clutchPerformanceWeights || {}),
    balancedScore: team.balancedScore || enhancedRankingSystem.calculateTeamScore(team, enhancedRankingSystem.balancedExcellenceWeights, attributeWeights.balancedExcellenceWeights || {})
  };
}

/**
 * Generate a summary of bracket picks
 */
function generateBracketSummary(brackets, allTeams) {
  // Count teams in Final Four across all brackets
  const finalFourCounts = {};
  
  // Count champions across all brackets
  const championCounts = {};
  
  // Track Cinderella teams (6th seed or lower reaching Sweet 16)
  const cinderellas = {};
  
  // Analyze all brackets
  Object.keys(brackets).forEach(bracketName => {
    const bracket = brackets[bracketName];
    
    // Count Final Four teams
    Object.values(bracket.regions).forEach(region => {
      const finalFourTeam = region.winner;
      finalFourCounts[finalFourTeam] = (finalFourCounts[finalFourTeam] || 0) + 1;
    });
    
    // Count champion
    const champion = bracket.champion;
    championCounts[champion] = (championCounts[champion] || 0) + 1;
    
    // Identify Cinderella teams
    Object.values(bracket.regions).forEach(region => {
      region.sweet16.forEach(game => {
        game.matchup.forEach(team => {
          const teamObj = bracket.teamMap[team];
          if (teamObj && parseInt(teamObj.Seed) >= 6) { // 6th seed or lower
            cinderellas[team] = (cinderellas[team] || 0) + 1;
          }
        });
      });
    });
  });
  
  // Sort final four teams by count
  const finalFourTeams = Object.keys(finalFourCounts)
    .map(team => ({ team, count: finalFourCounts[team] }))
    .sort((a, b) => b.count - a.count);
  
  // Sort champions by count
  const champions = Object.keys(championCounts)
    .map(team => ({ team, count: championCounts[team] }))
    .sort((a, b) => b.count - a.count);
    
  // Sort Cinderella teams by count
  const cinderellaTeams = Object.keys(cinderellas)
    .map(team => ({ team, count: cinderellas[team] }))
    .sort((a, b) => b.count - a.count);
  
  // Find teams that appear consistently
  const consistentFinalFour = finalFourTeams.filter(t => t.count >= Object.keys(brackets).length / 2);
  const consistentChampions = champions.filter(t => t.count >= Object.keys(brackets).length / 3);
  const consistentCinderellas = cinderellaTeams.filter(t => t.count >= 2); // Appear in at least 2 brackets
  
  // Get additional data about consistent teams
  const enhancedFinalFour = consistentFinalFour.map(item => {
    const team = allTeams.find(t => t.Team === item.team);
    return {
      ...item,
      seed: team ? team.Seed : "N/A",
      adjO: team ? team.AdjO : "N/A",
      adjD: team ? team.AdjD : "N/A"
    };
  });
  
  const enhancedChampions = consistentChampions.map(item => {
    const team = allTeams.find(t => t.Team === item.team);
    return {
      ...item,
      seed: team ? team.Seed : "N/A",
      adjO: team ? team.AdjO : "N/A",
      adjD: team ? team.AdjD : "N/A"
    };
  });
  
  const enhancedCinderellas = consistentCinderellas.map(item => {
    const team = allTeams.find(t => t.Team === item.team);
    return {
      ...item,
      seed: team ? team.Seed : "N/A",
      adjO: team ? team.AdjO : "N/A",
      adjD: team ? team.AdjD : "N/A",
      strengths: team ? enhancedRankingSystem.getTeamStrengths(team) : []
    };
  });
  
  return {
    finalFourTeams,
    champions,
    cinderellaTeams,
    consistentFinalFour: enhancedFinalFour,
    consistentChampions: enhancedChampions,
    consistentCinderellas: enhancedCinderellas,
    totalBrackets: Object.keys(brackets).length
  };
}

/**
 * Find upsets in a bracket
 */
function findUpsets(bracket) {
  const upsets = [];
  
  // Check each region
  Object.keys(bracket.regions).forEach(region => {
    const regionResults = bracket.regions[region];
    
    // Check each round for upsets
    ['roundOf32', 'sweet16', 'elite8'].forEach(round => {
      regionResults[round].forEach(game => {
        const teams = game.matchup;
        const winner = game.winner;
        
        // Get team objects
        const team1 = bracket.teamMap[teams[0]];
        const team2 = bracket.teamMap[teams[1]];
        
        if (team1 && team2) {
          const seed1 = parseInt(team1.Seed);
          const seed2 = parseInt(team2.Seed);
          const winnerTeam = winner === teams[0] ? team1 : team2;
          const loserTeam = winner === teams[0] ? team2 : team1;
          
          // If higher seed (larger number) beats lower seed (smaller number), it's an upset
          if ((winner === teams[0] && seed1 > seed2) || (winner === teams[1] && seed2 > seed1)) {
            // Consider meaningful upsets (seed difference > 2)
            if (Math.abs(seed1 - seed2) >= 2) {
              upsets.push({
                round,
                region,
                winner: winnerTeam.Team,
                loser: loserTeam.Team,
                winnerSeed: winnerTeam.Seed,
                loserSeed: loserTeam.Seed,
                // Add strengths of the winning underdog team
                winnerStrengths: enhancedRankingSystem.getTeamStrengths(winnerTeam).slice(0, 3) // Top 3 strengths
              });
            }
          }
        }
      });
    });
  });
  
  return upsets;
}

/**
 * Generate HTML visualization of bracket
 */
function generateBracketVisualization(bracket, filename) {
  // Create HTML for visualization
  let html = `
<!DOCTYPE html>
<html>
<head>
  <title>NCAA Tournament Bracket Visualization</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      padding: 20px;
      background-color: #f5f5f5;
    }
    h1, h2, h3 {
      color: #333;
    }
    .bracket-container {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      margin-bottom: 30px;
    }
    .region {
      flex: 1;
      min-width: 250px;
      margin: 0 10px 20px;
      background-color: white;
      border-radius: 8px;
      padding: 15px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .region-title {
      text-align: center;
      margin-bottom: 15px;
      padding-bottom: 10px;
      border-bottom: 1px solid #eee;
    }
    .round {
      margin-bottom: 20px;
    }
    .round-title {
      font-size: 14px;
      color: #666;
      margin-bottom: 10px;
    }
    .matchup {
      background-color: white;
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 10px;
      margin-bottom: 15px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .team {
      padding: 5px;
      margin: 2px 0;
      border-radius: 3px;
      display: flex;
      justify-content: space-between;
    }
    .team-seed {
      display: inline-block;
      width: 20px;
      text-align: center;
      margin-right: 5px;
      font-weight: bold;
      color: #555;
    }
    .winner {
      font-weight: bold;
      background-color: #e8f4f8;
    }
    .upset {
      background-color: #fff0f0;
    }
    .cinderella {
      background-color: #fff8e0;
    }
    .final-four {
      margin-top: 30px;
      background-color: white;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .championship {
      margin-top: 30px;
      background-color: #f0f8ff;
      border: 2px solid #4682b4;
      border-radius: 8px;
      padding: 20px;
      text-align: center;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .champion-card {
      display: inline-block;
      background-color: white;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.2);
      margin: 20px 0;
    }
    .strengths {
      font-size: 12px;
      color: #666;
      margin-top: 5px;
      font-style: italic;
    }
  </style>
</head>
<body>
  <h1>NCAA Tournament Bracket Visualization</h1>
  
  <div class="bracket-container">`;
    
  // Add each region
  Object.keys(bracket.regions).forEach(regionName => {
    const region = bracket.regions[regionName];
    
    html += `
    <div class="region">
      <h2 class="region-title">${regionName} Region</h2>
      
      <div class="round">
        <h3 class="round-title">Round of 32</h3>`;
      
      // First round results
      region.roundOf32.forEach(game => {
        const team1 = bracket.teamMap[game.matchup[0]];
        const team2 = bracket.teamMap[game.matchup[1]];
        const winner = game.winner;
        
        if (team1 && team2) {
          const seed1 = parseInt(team1.Seed);
          const seed2 = parseInt(team2.Seed);
          const isUpset = (winner === team1.Team && seed1 > seed2) || (winner === team2.Team && seed2 > seed1);
          
          html += `
        <div class="matchup">
          <div class="team ${team1.Team === winner ? 'winner' : ''} ${team1.Team === winner && seed1 > seed2 ? 'upset' : ''}">
            <span><span class="team-seed">${team1.Seed}</span> ${team1.Team}</span>
            <span>${Math.round(team1.weightedScore)}</span>
          </div>
          <div class="team ${team2.Team === winner ? 'winner' : ''} ${team2.Team === winner && seed2 > seed1 ? 'upset' : ''}">
            <span><span class="team-seed">${team2.Seed}</span> ${team2.Team}</span>
            <span>${Math.round(team2.weightedScore)}</span>
          </div>
        </div>`;
        }
      });
      
      html += `
      </div>
      
      <div class="round">
        <h3 class="round-title">Sweet 16</h3>`;
      
      // Sweet 16 matchups
      region.sweet16.forEach(game => {
        const team1 = bracket.teamMap[game.matchup[0]];
        const team2 = bracket.teamMap[game.matchup[1]];
        const winner = game.winner;
        
        if (team1 && team2) {
          const seed1 = parseInt(team1.Seed);
          const seed2 = parseInt(team2.Seed);
          const isUpset = (winner === team1.Team && seed1 > seed2) || (winner === team2.Team && seed2 > seed1);
          const isCinderella1 = seed1 >= 6;
          const isCinderella2 = seed2 >= 6;
          
          html += `
        <div class="matchup">
          <div class="team ${team1.Team === winner ? 'winner' : ''} ${team1.Team === winner && seed1 > seed2 ? 'upset' : ''} ${isCinderella1 ? 'cinderella' : ''}">
            <span><span class="team-seed">${team1.Seed}</span> ${team1.Team}</span>
            <span>${Math.round(team1.weightedScore)}</span>
          </div>
          <div class="team ${team2.Team === winner ? 'winner' : ''} ${team2.Team === winner && seed2 > seed1 ? 'upset' : ''} ${isCinderella2 ? 'cinderella' : ''}">
            <span><span class="team-seed">${team2.Seed}</span> ${team2.Team}</span>
            <span>${Math.round(team2.weightedScore)}</span>
          </div>
        </div>`;
        }
      });
      
      html += `
      </div>
      
      <div class="round">
        <h3 class="round-title">Elite 8</h3>`;
      
      // Elite 8 matchups
      region.elite8.forEach(game => {
        const team1 = bracket.teamMap[game.matchup[0]];
        const team2 = bracket.teamMap[game.matchup[1]];
        const winner = game.winner;
        
        if (team1 && team2) {
          const seed1 = parseInt(team1.Seed);
          const seed2 = parseInt(team2.Seed);
          const isUpset = (winner === team1.Team && seed1 > seed2) || (winner === team2.Team && seed2 > seed1);
          const isCinderella1 = seed1 >= 6;
          const isCinderella2 = seed2 >= 6;
          
          html += `
        <div class="matchup">
          <div class="team ${team1.Team === winner ? 'winner' : ''} ${team1.Team === winner && seed1 > seed2 ? 'upset' : ''} ${isCinderella1 ? 'cinderella' : ''}">
            <span><span class="team-seed">${team1.Seed}</span> ${team1.Team}</span>
            <span>${Math.round(team1.weightedScore)}</span>
          </div>
          <div class="team ${team2.Team === winner ? 'winner' : ''} ${team2.Team === winner && seed2 > seed1 ? 'upset' : ''} ${isCinderella2 ? 'cinderella' : ''}">
            <span><span class="team-seed">${team2.Seed}</span> ${team2.Team}</span>
            <span>${Math.round(team2.weightedScore)}</span>
          </div>
        </div>`;
        }
      });
      
      html += `
      </div>
      
      <div class="round">
        <h3 class="round-title">Final Four Representative</h3>
        <div class="matchup">
          <div class="team winner">
            <span class="team-seed">${bracket.teamMap[region.winner]?.Seed || 'N/A'}</span> ${region.winner}
          </div>
        </div>
      </div>
    </div>`;
  });
  
  // Add Final Four and Championship
  html += `
  </div>
  
  <div class="final-four">
    <h2>Final Four</h2>
    <div class="bracket-container">
      <div class="matchup" style="flex: 1; min-width: 300px;">
        <h3>${bracket.finalFour.semifinals[0].teams[0]} vs ${bracket.finalFour.semifinals[0].teams[1]}</h3>
        <div class="team winner">
          <span>Winner: ${bracket.finalFour.semifinals[0].winner}</span>
        </div>
      </div>
      
      <div class="matchup" style="flex: 1; min-width: 300px;">
        <h3>${bracket.finalFour.semifinals[1].teams[0]} vs ${bracket.finalFour.semifinals[1].teams[1]}</h3>
        <div class="team winner">
          <span>Winner: ${bracket.finalFour.semifinals[1].winner}</span>
        </div>
      </div>
    </div>
  </div>
  
  <div class="championship">
    <h2>Championship Game</h2>
    <h3>${bracket.championship.teams[0]} vs ${bracket.championship.teams[1]}</h3>
    <div class="champion-card">
      <h2>National Champion</h2>
      <h3>${bracket.champion} (${bracket.teamMap[bracket.champion]?.Seed || 'N/A'} Seed)</h3>`;
      
  // Add champion strengths if available
  const championTeam = bracket.teamMap[bracket.champion];
  if (championTeam) {
    const strengths = enhancedRankingSystem.getTeamStrengths(championTeam);
    if (strengths.length > 0) {
      html += `
      <div class="strengths">
        <strong>Key Strengths:</strong> ${strengths.slice(0, 5).join(", ")}
      </div>`;
    }
  }
      
  html += `
    </div>
  </div>
  
  <h2>Notable Upsets</h2>
  <ul>`;
    
  // Add notable upsets
  const upsets = findUpsets(bracket);
  if (upsets.length > 0) {
    upsets.forEach(upset => {
      html += `
    <li><strong>${upset.round} (${upset.region}):</strong> ${upset.winner} (${upset.winnerSeed}) over ${upset.loser} (${upset.loserSeed})`;
      
      if (upset.winnerStrengths && upset.winnerStrengths.length > 0) {
        html += ` - <span class="strengths">Key strengths: ${upset.winnerStrengths.join(", ")}</span>`;
      }
      
      html += `</li>`;
    });
  } else {
    html += `
    <li>No significant upsets predicted</li>`;
  }
    
  html += `
  </ul>
  
  <footer>
    <p>Generated on ${new Date().toLocaleDateString()} using Enhanced NCAA Tournament Bracket Generator</p>
  </footer>
</body>
</html>`;
    
  // Write the HTML to a file
  try {
    fs.writeFileSync(filename, html);
    console.log(`Bracket visualization saved to ${filename}`);
    return filename;
  } catch (error) {
    console.error("Error writing bracket visualization:", error);
    return null;
  }
}

// Export functions for use in other scripts
module.exports = {
  generateBrackets,
  findUpsets,
  processTeamData,
  generateBracketVisualization
};