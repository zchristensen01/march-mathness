// Runner script for the NCAA Tournament Bracket Generator
const fs = require('fs');
const bracketGenerator = require('./bracket_generator.js');
const enhancedRankingSystem = require('./enhanced_ranking_system.js');

// Function to run and display bracket results
async function runBracketGenerator() {
  console.log("==========================================");
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
  console.log("\n==========================================");
  console.log("MOST CONSISTENT FINAL FOUR PICKS");
  console.log("==========================================");
  results.summary.consistentFinalFour.forEach(team => {
    console.log(`${team.team} (${team.seed} seed): Selected in ${team.count}/${results.summary.totalBrackets} brackets`);
    console.log(`  - Adjusted Offense: ${Number(team.adjO).toFixed(1)}`);
    console.log(`  - Adjusted Defense: ${Number(team.adjD).toFixed(1)}`);
  });
  
  console.log("\n==========================================");
  console.log("MOST CONSISTENT CHAMPIONSHIP PICKS");
  console.log("==========================================");
  results.summary.consistentChampions.forEach(team => {
    console.log(`${team.team} (${team.seed} seed): Selected in ${team.count}/${results.summary.totalBrackets} brackets`);
    console.log(`  - Adjusted Offense: ${Number(team.adjO).toFixed(1)}`);
    console.log(`  - Adjusted Defense: ${Number(team.adjD).toFixed(1)}`);
  });
  
  // Log each bracket strategy
  console.log("\n==========================================");
  console.log("BRACKET STRATEGIES");
  console.log("==========================================");
  
  Object.keys(results.brackets).forEach(strategyName => {
    const bracket = results.brackets[strategyName];
    console.log(`\n--- ${strategyName.toUpperCase()} BRACKET STRATEGY ---`);
    
    console.log("\nFinal Four:");
    Object.keys(bracket.regions).forEach(region => {
      const winner = bracket.regions[region].winner;
      const team = results.teamMap ? results.teamMap[winner] : { Team: winner, Seed: "N/A" };
      console.log(`  - ${region}: ${team.Team} (${team.Seed} seed)`);
    });
    
    console.log("\nChampionship Game:");
    console.log(`  - ${bracket.championship.teams[0]} vs ${bracket.championship.teams[1]}`);
    
    console.log("\nChampion:");
    const champion = results.teamMap ? results.teamMap[bracket.champion] : { Team: bracket.champion, Seed: "N/A" };
    console.log(`  - ${champion.Team} (${champion.Seed} seed)`);
    
    // Highlight any notable upsets in this bracket
    const upsets = bracketGenerator.findUpsets(bracket);
    if (upsets.length > 0) {
      console.log("\nNotable Upsets:");
      upsets.forEach(upset => {
        console.log(`  - ${upset.round} (${upset.region}): ${upset.winner} (${upset.winnerSeed}) over ${upset.loser} (${upset.loserSeed})`);
      });
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
  
  // Save readable summary
  fs.writeFileSync('bracket_summary.txt', summaryText);
  console.log("Human-readable summary saved to bracket_summary.txt");
  
  // Save each bracket to a separate file
  Object.keys(results.brackets).forEach(strategyName => {
    const bracketFile = `bracket_${strategyName}.json`;
    fs.writeFileSync(bracketFile, JSON.stringify(results.brackets[strategyName], null, 2));
    console.log(`${strategyName} bracket saved to ${bracketFile}`);
  });
  
  console.log("\nBracket generation complete!");
}

// Run the function
runBracketGenerator().catch(error => {
  console.error("Error running bracket generator:", error);
});