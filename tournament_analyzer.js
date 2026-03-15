// NCAA Tournament Complete Analyzer
// This script analyzes teams and generates bracket predictions with enhanced research insights

const fs = require('fs');
const enhancedRankingSystem = require('./enhanced_ranking_system.js');
const bracketGenerator = require('./bracket_generator.js');

// Function to generate team rankings across all models
async function generateRankings() {
  console.log("==========================================");
  console.log("NCAA TOURNAMENT TEAM ANALYSIS");
  console.log("==========================================");
  
  // Load the CSV data
  console.log("Loading team data from CSV...");
  const csvData = fs.readFileSync('final_table.csv', 'utf8');
  
  // Process the CSV data into team objects
  const teams = enhancedRankingSystem.processCSV(csvData);
  console.log(`Loaded ${teams.length} teams from CSV`);
  
  // Output headers for all CSV files
  const outputHeaders = [
    'Rank', 'Team', 'Seed', 'Conference', 'Calculated_Score', 
    'AdjEM', 'AdjO', 'AdjD', 'Barthag', 'Record',
    'eFG%', 'Opp_eFG%', '3P%', '2P%',
    'TO%', 'Opp_TO%', 'AST_TO', 'OR%', 'DR%', 
    'FTR', 'Opp_FTR', 'Tempo', 'SOS', 'FT%', 
    'Quad1_Wins', 'Last_10_Games_Metric', 'Star_Player_Index', 
    'Bench_Minutes_Pct', 'KenPom_Rank', 'Torvik_Rank', 'Massey_Rank', 'NET_Rank',
    '2P_%_D', '3P_%_D', 'Blk_%', 'Blked_%', 'Ast_%', 'Op_Ast_%', 
    '3P_Rate', '3P_Rate_D', 'Exp', 'Elite_SOS', 'PPP_Off', 'PPP_Def',
    'Strengths'
  ];
  
  // 1. Default Rankings
  console.log("\nGenerating default rankings...");
  const defaultRanking = enhancedRankingSystem.recalculateScores(teams, enhancedRankingSystem.defaultWeights);
  const rankedTeams = generateRankedTeamsCSV(defaultRanking, 'default-rankings.csv', outputHeaders);
  
  // Display the top 25 teams
  console.log("\nTOP 25 NCAA TOURNAMENT TEAMS (DEFAULT WEIGHTS):");
  console.log("==========================================");
  rankedTeams.slice(0, 25).forEach((team) => {
    console.log(`${team.Rank}. ${team.Team} (${team.Seed} seed, ${team.Conference}): ${team.Calculated_Score}`);
  });
  
  // 2. Cinderella Teams Predictor (now 6th seed or lower)
  console.log("\nGenerating Cinderella Teams rankings...");
  const cinderellaRanking = enhancedRankingSystem.runAnalysis('cinderella', teams, enhancedRankingSystem.attributeWeights.cinderellaWeights);
  
  // Filter for only teams seeded 6 or lower
  const cinderellaTeams = cinderellaRanking
    .filter(team => parseInt(team.Seed) >= 6)
    .slice(0, 15); // Get the top 15
  
  generateRankedTeamsCSV(cinderellaTeams, 'cinderella-rankings.csv', outputHeaders);
  
  // Display the top 10 Cinderella candidates
  console.log("\nTOP 10 CINDERELLA CANDIDATES (6TH SEED OR LOWER):");
  console.log("==========================================");
  cinderellaTeams.slice(0, 10).forEach((team, index) => {
    console.log(`${index + 1}. ${team.Team} (${team.Seed} seed, ${team.Conference}): ${team.Calculated_Score}`);
    
    // Get team strengths
    const strengths = enhancedRankingSystem.getTeamStrengths(team);
    if (strengths.length > 0) {
      console.log(`   Key strengths: ${strengths.join(", ")}`);
    }
  });
  
  // 3. Best Defensive Teams
  console.log("\nGenerating Best Defensive Teams rankings...");
  const defensiveRanking = enhancedRankingSystem.runAnalysis('defensive', teams, enhancedRankingSystem.attributeWeights);
  const defensiveTeams = generateRankedTeamsCSV(defensiveRanking, 'defensive-rankings.csv', outputHeaders);
  
  // Display the top 10 defensive teams
  console.log("\nTOP 10 DEFENSIVE TEAMS:");
  console.log("==========================================");
  defensiveTeams.slice(0, 10).forEach((team) => {
    console.log(`${team.Rank}. ${team.Team} (${team.Seed} seed, ${team.Conference}): ${team.Calculated_Score}`);
  });
  
  // 4. Offensive Powerhouses
  console.log("\nGenerating Offensive Powerhouses rankings...");
  const offensiveRanking = enhancedRankingSystem.runAnalysis('offensive', teams, enhancedRankingSystem.attributeWeights);
  const offensiveTeams = generateRankedTeamsCSV(offensiveRanking, 'offensive-rankings.csv', outputHeaders);
  
  // Display the top 10 offensive teams
  console.log("\nTOP 10 OFFENSIVE POWERHOUSES:");
  console.log("==========================================");
  offensiveTeams.slice(0, 10).forEach((team) => {
    console.log(`${team.Rank}. ${team.Team} (${team.Seed} seed, ${team.Conference}): ${team.Calculated_Score}`);
  });
  
  // 5. Momentum-Based Teams
  console.log("\nGenerating Momentum-Based Teams rankings...");
  const momentumRanking = enhancedRankingSystem.runAnalysis('momentum', teams, enhancedRankingSystem.attributeWeights);
  const momentumTeams = generateRankedTeamsCSV(momentumRanking, 'momentum-rankings.csv', outputHeaders);
  
  // Display the top 10 momentum teams
  console.log("\nTOP 10 TEAMS WITH BEST MOMENTUM/FORM:");
  console.log("==========================================");
  momentumTeams.slice(0, 10).forEach((team) => {
    console.log(`${team.Rank}. ${team.Team} (${team.Seed} seed, ${team.Conference}): ${team.Calculated_Score}`);
  });
  
  // 6. Giant-Killers
  console.log("\nGenerating Giant-Killers rankings...");
  const giantKillerRanking = enhancedRankingSystem.runAnalysis('giantkiller', teams, enhancedRankingSystem.attributeWeights);
  
  // Filter for only teams seeded 6 or lower for giant killers as well
  const giantKillerTeams = giantKillerRanking
    .filter(team => parseInt(team.Seed) >= 6)
    .slice(0, 15); // Get the top 15
    
  generateRankedTeamsCSV(giantKillerTeams, 'giant-killer-rankings.csv', outputHeaders);
  
  // Display the top 10 giant killer teams
  console.log("\nTOP 10 GIANT-KILLERS (TEAMS THAT CAN UPSET HIGHER SEEDS):");
  console.log("==========================================");
  giantKillerTeams.slice(0, 10).forEach((team, index) => {
    console.log(`${index + 1}. ${team.Team} (${team.Seed} seed, ${team.Conference}): ${team.Calculated_Score}`);
  });
  
  // 7. Run upset analysis
  const upsetPicks = enhancedRankingSystem.runAnalysis('upset', teams, enhancedRankingSystem.attributeWeights);
  console.log("\nPOTENTIAL FIRST ROUND UPSETS (BASED ON TOURNAMENT BRACKET):");
  console.log("==========================================");
  upsetPicks.forEach((team, index) => {
    console.log(`${index + 1}. [${team.region}] ${team.Seed} ${team.Team} (${team.Calculated_Score}) over ${team.opponentSeed} ${team.opponent} (${team.opponentScore}) - Upset Potential: ${team.upsetPotential}`);
  });
  
  // 8. Create a Final Four prediction
  const finalFour = enhancedRankingSystem.runAnalysis('final4', teams, enhancedRankingSystem.attributeWeights);
  console.log("\nPREDICTED FINAL FOUR TEAMS:");
  console.log("==========================================");
  finalFour.forEach((team, index) => {
    console.log(`${index + 1}. ${team.region}: ${team.team.Team} (${team.team.Seed} seed, ${team.team.Conference}): ${team.team.Calculated_Score}`);
    console.log(`   Strengths: ${team.strengths.join(", ")}`);
  });
  
  // Return all ranking results for potential further analysis
  return {
    teams,
    rankings: {
      default: rankedTeams,
      cinderella: cinderellaTeams,
      defensive: defensiveTeams,
      offensive: offensiveTeams,
      momentum: momentumTeams,
      giantKiller: giantKillerTeams
    },
    predictions: {
      upsetPicks,
      finalFour
    }
  };
}

// Function to generate ranked teams CSV
function generateRankedTeamsCSV(rankedTeams, filename, outputHeaders) {
  // Add rank to each team
  const rankedWithIndex = rankedTeams.map((team, index) => {
    // Add strengths to each team for the CSV
    const strengths = enhancedRankingSystem.getTeamStrengths(team).join("; ");
    
    return { 
      Rank: index + 1, 
      ...team,
      Strengths: strengths
    };
  });
  
  // Generate CSV
  const outputCSV = generateCSV(rankedWithIndex, outputHeaders);
  
  // Save to file
  fs.writeFileSync(filename, outputCSV);
  console.log(`Rankings saved to ${filename}`);
  
  return rankedWithIndex;
}

// Helper function to generate CSV
function generateCSV(data, headers) {
  // Start with headers
  let csv = headers.join(',') + '\n';
  
  // Add each row
  data.forEach(row => {
    const values = headers.map(header => {
      const value = row[header];
      // Handle strings with commas by quoting them
      if (typeof value === 'string' && value.includes(',')) {
        return `"${value}"`;
      }
      return value !== undefined ? value : '';
    });
    
    csv += values.join(',') + '\n';
  });
  
  return csv;
}

// Function to generate brackets
async function generateBrackets() {
  console.log("\n==========================================");
  console.log("NCAA TOURNAMENT BRACKET GENERATOR");
  console.log("==========================================");
  
  // Generate brackets
  console.log("\nGenerating bracket options...");
  const results = await bracketGenerator.generateBrackets();
  
  if (results.error) {
    console.error(`Error: ${results.error}`);
    return;
  }
  
  // Display summary of consistent picks
  console.log("\nMOST CONSISTENT FINAL FOUR PICKS:");
  console.log("==========================================");
  results.summary.consistentFinalFour.forEach(team => {
    console.log(`${team.team} (${team.seed} seed): Selected in ${team.count}/${results.summary.totalBrackets} brackets`);
    console.log(`  - Adjusted Offense: ${Number(team.adjO).toFixed(1)}`);
    console.log(`  - Adjusted Defense: ${Number(team.adjD).toFixed(1)}`);
  });
  
  console.log("\nMOST CONSISTENT CHAMPIONSHIP PICKS:");
  console.log("==========================================");
  results.summary.consistentChampions.forEach(team => {
    console.log(`${team.team} (${team.seed} seed): Selected in ${team.count}/${results.summary.totalBrackets} brackets`);
    console.log(`  - Adjusted Offense: ${Number(team.adjO).toFixed(1)}`);
    console.log(`  - Adjusted Defense: ${Number(team.adjD).toFixed(1)}`);
  });
  
  console.log("\nMOST CONSISTENT CINDERELLA TEAMS (6TH SEED OR LOWER):");
  console.log("==========================================");
  if (results.summary.consistentCinderellas && results.summary.consistentCinderellas.length > 0) {
    results.summary.consistentCinderellas.forEach(team => {
      console.log(`${team.team} (${team.seed} seed): Selected in ${team.count} brackets`);
      if (team.strengths && team.strengths.length > 0) {
        console.log(`  - Key strengths: ${team.strengths.slice(0, 3).join(", ")}`);
      }
    });
  } else {
    console.log("No consistent Cinderella teams found across bracket strategies");
  }
  
  // Log each bracket strategy
  console.log("\nBRACKET STRATEGIES:");
  console.log("==========================================");
  
  Object.keys(results.brackets).forEach(strategyName => {
    const bracket = results.brackets[strategyName];
    console.log(`\n--- ${strategyName.toUpperCase()} BRACKET STRATEGY ---`);
    
    console.log("\nFinal Four:");
    Object.keys(bracket.regions).forEach(region => {
      const winner = bracket.regions[region].winner;
      const team = results.teamMap ? results.teamMap[winner] : null;
      const teamSeed = team ? team.Seed : "N/A";
      console.log(`  - ${region}: ${winner} (${teamSeed} seed)`);
    });
    
    console.log("\nChampionship Game:");
    console.log(`  - ${bracket.championship.teams[0]} vs ${bracket.championship.teams[1]}`);
    
    console.log("\nChampion:");
    const champion = bracket.champion;
    const championTeam = results.teamMap ? results.teamMap[champion] : null;
    const championSeed = championTeam ? championTeam.Seed : "N/A";
    console.log(`  - ${champion} (${championSeed} seed)`);
    
    // Highlight any notable upsets in this bracket
    const upsets = bracketGenerator.findUpsets(bracket);
    if (upsets.length > 0) {
      console.log("\nNotable Upsets:");
      upsets.forEach(upset => {
        console.log(`  - ${upset.round} (${upset.region}): ${upset.winner} (${upset.winnerSeed}) over ${upset.loser} (${upset.loserSeed})`);
        if (upset.winnerStrengths && upset.winnerStrengths.length > 0) {
          console.log(`    Key strengths: ${upset.winnerStrengths.join(", ")}`);
        }
      });
    }
    
    // Generate visual HTML representation of the bracket
    try {
      const htmlFile = `bracket_${strategyName}.html`;
      bracketGenerator.generateBracketVisualization(bracket, htmlFile);
    } catch (error) {
      console.error(`Error generating visualization for ${strategyName} bracket:`, error);
    }
  });
  
  // Export summary to file
  console.log("\n==========================================");
  console.log("GENERATING OUTPUT FILES");
  console.log("==========================================");
  
  // Save summary to JSON
  fs.writeFileSync('bracket_summary.json', JSON.stringify(results.summary, null, 2));
  console.log("Summary saved to bracket_summary.json");
  
  // Create a readable summary
  let summaryText = "NCAA TOURNAMENT BRACKET GENERATOR RESULTS\n\n";
  summaryText += "MOST CONSISTENT FINAL FOUR PICKS:\n";
  results.summary.consistentFinalFour.forEach(team => {
    summaryText += `- ${team.team} (${team.seed} seed): Selected in ${team.count}/${results.summary.totalBrackets} brackets\n`;
  });
  
  summaryText += "\nMOST CONSISTENT CHAMPIONSHIP PICKS:\n";
  results.summary.consistentChampions.forEach(team => {
    summaryText += `- ${team.team} (${team.seed} seed): Selected in ${team.count}/${results.summary.totalBrackets} brackets\n`;
  });
  
  summaryText += "\nMOST CONSISTENT CINDERELLA TEAMS (6TH SEED OR LOWER):\n";
  if (results.summary.consistentCinderellas && results.summary.consistentCinderellas.length > 0) {
    results.summary.consistentCinderellas.forEach(team => {
      summaryText += `- ${team.team} (${team.seed} seed): Selected in ${team.count} brackets\n`;
    });
  } else {
    summaryText += "- No consistent Cinderella teams found\n";
  }
  
  // Save readable summary
  fs.writeFileSync('bracket_summary.txt', summaryText);
  console.log("Human-readable summary saved to bracket_summary.txt");
  
  // Save each bracket to a separate file
  Object.keys(results.brackets).forEach(strategyName => {
    const bracketFile = `bracket_${strategyName}.json`;
    fs.writeFileSync(bracketFile, JSON.stringify(results.brackets[strategyName], null, 2));
    console.log(`${strategyName} bracket saved to ${bracketFile}`);
  });
  
  return results;
}

console.log("Starting to generate rankings...");
generateRankings()
  .then(rankingResults => {
    console.log("Rankings generated successfully");
    // Optionally generate brackets after rankings
    return generateBrackets();
  })
  .then(() => {
    console.log("All processes completed successfully");
  })
  .catch(error => {
    console.error("Error during execution:", error);
  });