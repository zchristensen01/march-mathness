// NCAA Tournament Analysis Tool
// This script uses the enhanced ranking system to analyze tournament teams

const enhancedRankingSystem = require('./enhanced_ranking_system.js');

// Function to run a comprehensive analysis on all tournament teams
async function analyzeAllTeams() {
  try {
    // Load team data
    const csvData = await window.fs.readFile('final_table.csv', { encoding: 'utf8' });
    const teams = enhancedRankingSystem.processCSV(csvData);
    
    // Generate rankings for each specialized model
    const rankings = {
      championship: enhancedRankingSystem.runAnalysis('championship', teams),
      cinderella: enhancedRankingSystem.runAnalysis('cinderella', teams),
      defensive: enhancedRankingSystem.runAnalysis('defensive', teams),
      offensive: enhancedRankingSystem.runAnalysis('offensive', teams),
      momentum: enhancedRankingSystem.runAnalysis('momentum', teams),
      giantKiller: enhancedRankingSystem.runAnalysis('giantkiller', teams),
      physical: enhancedRankingSystem.runAnalysis('physical', teams),
      experience: enhancedRankingSystem.runAnalysis('experience', teams),
      clutch: enhancedRankingSystem.runAnalysis('clutch', teams),
      balanced: enhancedRankingSystem.runAnalysis('balanced', teams)
    };
    
    // Find potential upsets
    const upsets = enhancedRankingSystem.identifyUpsetPotential(teams);
    
    // Predict Final Four
    const finalFour = enhancedRankingSystem.predictFinalFour(teams);
    
    // Identify undervalued teams (teams that perform well across multiple models)
    const undervaluedTeams = findUndervaluedTeams(teams, rankings);
    
    // Return comprehensive analysis results
    return {
      rankings,
      upsets,
      finalFour,
      undervaluedTeams,
      // Add specific analyses for different types of teams
      potentialCinderellas: enhancedRankingSystem.identifyCinderellas(teams).slice(0, 10),
      defensivePowerhouses: rankings.defensive.slice(0, 10),
      offensivePowerhouses: rankings.offensive.slice(0, 10),
      momentumTeams: rankings.momentum.slice(0, 10),
      experiencedTeams: rankings.experience.slice(0, 10),
      bestClutchTeams: rankings.clutch.slice(0, 10),
      mostBalancedTeams: rankings.balanced.slice(0, 10),
      physicalDominators: rankings.physical.slice(0, 10)
    };
  } catch (error) {
    console.error("Error analyzing teams:", error);
    return { error: error.message };
  }
}

// Find undervalued teams (outperforming their seed across multiple models)
function findUndervaluedTeams(teams, rankings) {
  // Create a map of seeds to their expected performance level
  const seedExpectations = {};
  for (let i = 1; i <= 16; i++) {
    seedExpectations[i] = 100 - ((i - 1) * 6); // Linear decrease in expected score
  }
  
  // Calculate an "undervalued score" for each team
  const undervaluedScores = teams.map(team => {
    const seed = parseInt(team.Seed);
    const seedExpectation = seedExpectations[seed] || 40; // Default for unknown seeds
    
    // Create a map of all models this team overperforms in
    const modelOverperformance = {};
    let totalOverperformance = 0;
    let modelsOverperforming = 0;
    
    // Check each model
    Object.keys(rankings).forEach(model => {
      const teamInModel = rankings[model].find(t => t.Team === team.Team);
      if (teamInModel) {
        const overperformance = teamInModel.Calculated_Score - seedExpectation;
        if (overperformance > 0) {
          modelOverperformance[model] = overperformance;
          totalOverperformance += overperformance;
          modelsOverperforming++;
        }
      }
    });
    
    // Calculate an undervalued score that considers both magnitude and consistency
    const undervaluedScore = totalOverperformance * Math.sqrt(modelsOverperforming);
    
    return {
      team: team.Team,
      seed: team.Seed,
      conference: team.Conference,
      undervaluedScore,
      modelsOverperforming,
      modelOverperformance
    };
  });
  
  // Sort by undervalued score and return top 10
  return undervaluedScores
    .sort((a, b) => b.undervaluedScore - a.undervaluedScore)
    .filter(team => team.modelsOverperforming >= 3) // Team must overperform in at least 3 models
    .slice(0, 10);
}

// Calculate optimal brackets based on different strategies
function generateOptimalBrackets(teams) {
  // We'll create several bracket strategies
  const strategies = {
    // Conservative strategy - mostly favorites with a few calculated upsets
    conservative: createBracketStrategy(teams, {
      championshipWeight: 0.6,
      clutchWeight: 0.2,
      balancedWeight: 0.2,
      upsetThreshold: 0.7 // Only pick strong upsets
    }),
    
    // Balanced strategy - good mix of favorites and upsets
    balanced: createBracketStrategy(teams, {
      championshipWeight: 0.4,
      momentumWeight: 0.2,
      clutchWeight: 0.2,
      giantKillerWeight: 0.2,
      upsetThreshold: 0.5
    }),
    
    // High risk strategy - more upsets, emphasis on momentum and giant-killers
    highRisk: createBracketStrategy(teams, {
      championshipWeight: 0.2,
      momentumWeight: 0.3,
      giantKillerWeight: 0.3,
      cinderellaWeight: 0.2,
      upsetThreshold: 0.4
    }),
    
    // Analytics-driven - pure numbers approach
    analytics: createBracketStrategy(teams, {
      championshipWeight: 0.3,
      balancedWeight: 0.3,
      clutchWeight: 0.2,
      momentumWeight: 0.2,
      upsetThreshold: 0.6
    })
  };
  
  return strategies;
}

// Create a bracket strategy based on specified weights
function createBracketStrategy(teams, weights) {
  // Composite score calculation based on weights
  const teamScores = teams.map(team => {
    const modelScores = enhancedRankingSystem.calculateAllModelScores(team);
    
    // Calculate composite score
    let compositeScore = 0;
    if (weights.championshipWeight) compositeScore += modelScores.championshipScore * weights.championshipWeight;
    if (weights.momentumWeight) compositeScore += modelScores.momentumScore * weights.momentumWeight;
    if (weights.clutchWeight) compositeScore += modelScores.clutchScore * weights.clutchWeight;
    if (weights.balancedWeight) compositeScore += modelScores.balancedScore * weights.balancedWeight;
    if (weights.giantKillerWeight) compositeScore += modelScores.giantKillerScore * weights.giantKillerWeight;
    if (weights.cinderellaWeight) compositeScore += modelScores.cinderellaScore * weights.cinderellaWeight;
    
    return {
      team: team.Team,
      seed: team.Seed,
      compositeScore,
      modelScores
    };
  });
  
  // Simulate tournament based on this strategy's weights
  const simulation = simulateTournamentWithStrategy(teamScores, weights.upsetThreshold);
  
  return {
    weights,
    simulation
  };
}

// Simulate tournament with a specific strategy
function simulateTournamentWithStrategy(teamScores, upsetThreshold) {
  // This is a simplified simulation - in a real implementation, you would
  // use the actual bracket and matchups to simulate each game
  
  // For this example, we'll just identify likely upsets and winners
  const regions = ['East', 'West', 'South', 'Midwest'];
  const results = {
    regions: {},
    finalFour: [],
    championship: null
  };
  
  // Group teams by region and simulate
  regions.forEach(region => {
    // In a real implementation, you would get the actual teams in this region
    // and simulate the matchups
    results.regions[region] = {
      winner: `Winner of ${region}`
    };
  });
  
  return results;
}

// Run the analysis
analyzeAllTeams().then(results => {
  console.log("NCAA Tournament Analysis Results:", results);
  
  // Extract top teams by category for display
  const championshipContenders = results.rankings.championship.slice(0, 10);
  console.log("\nTop Championship Contenders:");
  championshipContenders.forEach((team, index) => {
    console.log(`${index + 1}. ${team.Team} (${team.Seed}) - Score: ${team.Calculated_Score}`);
  });
  
  console.log("\nTop Cinderella Candidates:");
  results.potentialCinderellas.forEach((team, index) => {
    console.log(`${index + 1}. ${team.Team} (${team.Seed}) - Score: ${team.Calculated_Score}`);
  });
  
  console.log("\nTop Defensive Teams:");
  results.defensivePowerhouses.forEach((team, index) => {
    console.log(`${index + 1}. ${team.Team} (${team.Seed}) - Score: ${team.Calculated_Score}`);
  });
  
  console.log("\nTop Offensive Teams:");
  results.offensivePowerhouses.forEach((team, index) => {
    console.log(`${index + 1}. ${team.Team} (${team.Seed}) - Score: ${team.Calculated_Score}`);
  });
  
  console.log("\nTeams with the Most Momentum:");
  results.momentumTeams.forEach((team, index) => {
    console.log(`${index + 1}. ${team.Team} (${team.Seed}) - Score: ${team.Calculated_Score}`);
  });
  
  console.log("\nUndervalued Teams (Outperforming Seed):");
  results.undervaluedTeams.forEach((team, index) => {
    console.log(`${index + 1}. ${team.team} (${team.seed}) - Overperforming in ${team.modelsOverperforming} models`);
  });
  
  console.log("\nPotential First Round Upsets:");
  results.upsets.forEach((upset, index) => {
    console.log(`${index + 1}. ${upset.underdogName} (${upset.underdogSeed}) over ${upset.favoriteName} (${upset.favoriteSeed}) - Potential: ${upset.upsetPotential}`);
    console.log(`   Underdog strengths: ${upset.underdogStrengths.join(", ")}`);
    console.log(`   Matchup advantage: ${upset.matchupAdvantage.join(", ")}`);
  });
  
  console.log("\nPredicted Final Four:");
  results.finalFour.forEach(team => {
    console.log(`${team.region}: ${team.team.Team} (${team.team.Seed}) - Strengths: ${team.strengths.join(", ")}`);
  });
  
  // Generate bracket strategies
  const bracketStrategies = generateOptimalBrackets(results.rankings.championship);
  console.log("\nBracket Strategies Generated:", Object.keys(bracketStrategies));
});