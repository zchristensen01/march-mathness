// NCAA Tournament Bracket Visualizer
// This script generates a visual representation of the tournament brackets

const fs = require('fs');
const path = require('path');
const bracketGenerator = require('./bracket_generator.js');

/**
 * Generate an HTML visualization of a tournament bracket
 */
async function generateBracketVisualization(bracketType = 'standard') {
  try {
    // Generate the brackets
    console.log(`Generating ${bracketType} bracket visualization...`);
    const results = await bracketGenerator.generateBrackets();
    
    if (results.error) {
      console.error(`Error: ${results.error}`);
      return;
    }
    
    // Get the specified bracket
    const bracket = results.brackets[bracketType];
    if (!bracket) {
      console.error(`Bracket type '${bracketType}' not found. Available types: ${Object.keys(results.brackets).join(', ')}`);
      return;
    }
    
    // Create HTML for visualization
    let html = `
<!DOCTYPE html>
<html>
<head>
  <title>NCAA Tournament Bracket - ${bracketType} Strategy</title>
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
      justify-content: space-between;
      overflow-x: auto;
      margin-bottom: 30px;
    }
    .region {
      flex: 1;
      margin: 0 10px;
      min-width: 200px;
    }
    .round {
      margin-bottom: 20px;
    }
    .matchup {
      background-color: white;
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 10px;
      margin-bottom: 15px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .team {
      padding: 5px;
      margin: 2px 0;
      border-radius: 3px;
    }
    .winner {
      font-weight: bold;
      background-color: #e8f4f8;
    }
    .upset {
      background-color: #fff0f0;
    }
    .final-four {
      background-color: #f9f9f9;
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 15px;
      margin-top: 20px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .championship {
      background-color: #f0f8ff;
      border: 2px solid #4682b4;
      border-radius: 6px;
      padding: 20px;
      margin-top: 20px;
      text-align: center;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .strategy-info {
      background-color: #f9f9f9;
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 15px;
      margin-bottom: 20px;
    }
    .team-seed {
      display: inline-block;
      width: 25px;
      text-align: center;
      margin-right: 5px;
      font-weight: bold;
      color: #555;
    }
  </style>
</head>
<body>
  <h1>NCAA Tournament Bracket - ${bracketType.charAt(0).toUpperCase() + bracketType.slice(1)} Strategy</h1>
  
  <div class="strategy-info">
    <h3>Strategy Weights:</h3>
    <ul>
      ${Object.entries(bracket.weights)
        .filter(([key, value]) => value !== undefined && key !== 'upsetThreshold')
        .map(([key, value]) => `<li>${key.replace('Weight', '')}: ${(value * 100).toFixed(0)}%</li>`)
        .join('')}
    </ul>
    <p>Upset Threshold: ${bracket.weights.upsetThreshold.toFixed(2)}</p>
  </div>
  
  <h2>Regional Brackets</h2>
  <div class="bracket-container">`;
    
    // Add each region
    Object.keys(bracket.regions).forEach(regionName => {
      const region = bracket.regions[regionName];
      
      html += `
    <div class="region">
      <h3>${regionName} Region</h3>
      
      <div class="round">
        <h4>Round of 64</h4>`;
      
      // First round matchups
      region.roundOf32.forEach(game => {
        const team1 = results.teamMap[game.matchup[0]];
        const team2 = results.teamMap[game.matchup[1]];
        const winner = game.winner;
        
        if (team1 && team2) {
          const seed1 = parseInt(team1.Seed);
          const seed2 = parseInt(team2.Seed);
          const isUpset = (winner === team1.Team && seed1 > seed2) || (winner === team2.Team && seed2 > seed1);
          
          html += `
        <div class="matchup">
          <div class="team ${team1.Team === winner ? 'winner' : ''} ${team1.Team === winner && seed1 > seed2 ? 'upset' : ''}">
            <span class="team-seed">${team1.Seed}</span> ${team1.Team}
          </div>
          <div class="team ${team2.Team === winner ? 'winner' : ''} ${team2.Team === winner && seed2 > seed1 ? 'upset' : ''}">
            <span class="team-seed">${team2.Seed}</span> ${team2.Team}
          </div>
        </div>`;
        }
      });
      
      html += `
      </div>
      
      <div class="round">
        <h4>Round of 32</h4>`;
      
      // Sweet 16 matchups
      region.sweet16.forEach(game => {
        const team1 = results.teamMap[game.matchup[0]];
        const team2 = results.teamMap[game.matchup[1]];
        const winner = game.winner;
        
        if (team1 && team2) {
          const seed1 = parseInt(team1.Seed);
          const seed2 = parseInt(team2.Seed);
          const isUpset = (winner === team1.Team && seed1 > seed2) || (winner === team2.Team && seed2 > seed1);
          
          html += `
        <div class="matchup">
          <div class="team ${team1.Team === winner ? 'winner' : ''} ${team1.Team === winner && seed1 > seed2 ? 'upset' : ''}">
            <span class="team-seed">${team1.Seed}</span> ${team1.Team}
          </div>
          <div class="team ${team2.Team === winner ? 'winner' : ''} ${team2.Team === winner && seed2 > seed1 ? 'upset' : ''}">
            <span class="team-seed">${team2.Seed}</span> ${team2.Team}
          </div>
        </div>`;
        }
      });
      
      html += `
      </div>
      
      <div class="round">
        <h4>Sweet 16</h4>`;
      
      // Elite 8 matchups
      region.elite8.forEach(game => {
        const team1 = results.teamMap[game.matchup[0]];
        const team2 = results.teamMap[game.matchup[1]];
        const winner = game.winner;
        
        if (team1 && team2) {
          const seed1 = parseInt(team1.Seed);
          const seed2 = parseInt(team2.Seed);
          const isUpset = (winner === team1.Team && seed1 > seed2) || (winner === team2.Team && seed2 > seed1);
          
          html += `
        <div class="matchup">
          <div class="team ${team1.Team === winner ? 'winner' : ''} ${team1.Team === winner && seed1 > seed2 ? 'upset' : ''}">
            <span class="team-seed">${team1.Seed}</span> ${team1.Team}
          </div>
          <div class="team ${team2.Team === winner ? 'winner' : ''} ${team2.Team === winner && seed2 > seed1 ? 'upset' : ''}">
            <span class="team-seed">${team2.Seed}</span> ${team2.Team}
          </div>
        </div>`;
        }
      });
      
      html += `
      </div>
      
      <div class="round">
        <h4>Elite 8</h4>`;
      
      // Final Four matchups
      region.finalFour.forEach(game => {
        const team1 = results.teamMap[game.matchup[0]];
        const team2 = results.teamMap[game.matchup[1]];
        const winner = game.winner;
        
        if (team1 && team2) {
          const seed1 = parseInt(team1.Seed);
          const seed2 = parseInt(team2.Seed);
          const isUpset = (winner === team1.Team && seed1 > seed2) || (winner === team2.Team && seed2 > seed1);
          
          html += `
        <div class="matchup">
          <div class="team ${team1.Team === winner ? 'winner' : ''} ${team1.Team === winner && seed1 > seed2 ? 'upset' : ''}">
            <span class="team-seed">${team1.Seed}</span> ${team1.Team}
          </div>
          <div class="team ${team2.Team === winner ? 'winner' : ''} ${team2.Team === winner && seed2 > seed1 ? 'upset' : ''}">
            <span class="team-seed">${team2.Seed}</span> ${team2.Team}
          </div>
        </div>`;
        }
      });
      
      html += `
      </div>
    </div>`;
    });
    
    // Add Final Four and Championship
    html += `
  </div>
  
  <h2>Final Four</h2>
  <div class="final-four">
    <div class="matchup">
      <h3>${bracket.finalFour.semifinals[0].teams[0]} vs ${bracket.finalFour.semifinals[0].teams[1]}</h3>
      <div class="team winner">Winner: ${bracket.finalFour.semifinals[0].winner}</div>
    </div>
    
    <div class="matchup">
      <h3>${bracket.finalFour.semifinals[1].teams[0]} vs ${bracket.finalFour.semifinals[1].teams[1]}</h3>
      <div class="team winner">Winner: ${bracket.finalFour.semifinals[1].winner}</div>
    </div>
  </div>
  
  <h2>Championship Game</h2>
  <div class="championship">
    <h3>${bracket.championship.teams[0]} vs ${bracket.championship.teams[1]}</h3>
    <div class="team winner" style="font-size: 1.5em;">
      National Champion: ${bracket.champion}
    </div>
  </div>
  
  <h2>Notable Upsets</h2>
  <ul>`;
    
    // Add notable upsets
    const upsets = bracketGenerator.findUpsets(bracket);
    if (upsets.length > 0) {
      upsets.forEach(upset => {
        html += `
    <li><strong>${upset.round} (${upset.region}):</strong> ${upset.winner} (${upset.winnerSeed}) over ${upset.loser} (${upset.loserSeed})</li>`;
      });
    } else {
      html += `
    <li>No significant upsets predicted</li>`;
    }
    
    html += `
  </ul>
  
  <footer>
    <p>Generated on ${new Date().toLocaleDateString()} using NCAA Tournament Bracket Generator</p>
  </footer>
</body>
</html>`;
    
    // Write the HTML to a file
    const fileName = `bracket_${bracketType}.html`;
    fs.writeFileSync(fileName, html);
    console.log(`Bracket visualization saved to ${fileName}`);
    
    return fileName;
  } catch (error) {
    console.error("Error generating bracket visualization:", error);
    return null;
  }
}

// Generate visualizations for each bracket type
async function generateAllVisualizations() {
  // Standard bracket types
  const bracketTypes = [
    'standard',
    'favorites',
    'upsets',
    'analytics',
    'cinderella',
    'physical',
    'momentum',
    'experience'
  ];
  
  console.log("Generating bracket visualizations...");
  
  for (const type of bracketTypes) {
    await generateBracketVisualization(type);
  }
  
  console.log("All bracket visualizations generated!");
}

// If running directly, generate all visualizations
if (require.main === module) {
  generateAllVisualizations();
} else {
  // Export for use in other scripts
  module.exports = {
    generateBracketVisualization,
    generateAllVisualizations
  };
}