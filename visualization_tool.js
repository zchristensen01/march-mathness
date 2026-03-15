// NCAA Tournament Visualization Dashboard
// This script creates a visual dashboard for the tournament predictions

const fs = require('fs');
const path = require('path');

/**
 * Generate an HTML dashboard to view all tournament analysis results
 */
function generateDashboard() {
  // Read the bracket summary
  const summary = JSON.parse(fs.readFileSync('bracket_summary.json', 'utf8'));
  
  // Read other data files if they exist
  let defaultRankings = [];
  let cinderellaRankings = [];
  let upsets = [];
  
  try {
    // Try to read the CSV files and parse them
    defaultRankings = readCSV('default-rankings.csv');
    cinderellaRankings = readCSV('cinderella-rankings.csv');
  } catch (error) {
    console.error("Error reading ranking files:", error.message);
  }
  
  // Create HTML dashboard
  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NCAA Tournament Analysis Dashboard</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
      background-color: #f8f9fa;
    }
    .header {
      background-color: #0e4c92;
      color: white;
      padding: 20px;
      border-radius: 8px;
      margin-bottom: 20px;
      text-align: center;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .container {
      display: flex;
      flex-wrap: wrap;
      gap: 20px;
      justify-content: space-between;
    }
    .card {
      background: white;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 2px 5px rgba(0,0,0,0.1);
      flex: 1;
      min-width: 300px;
      margin-bottom: 20px;
    }
    h1, h2, h3 {
      color: #0e4c92;
    }
    h1 {
      margin-top: 0;
    }
    h2 {
      border-bottom: 2px solid #eee;
      padding-bottom: 10px;
      margin-top: 0;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
    }
    th, td {
      padding: 12px 15px;
      border-bottom: 1px solid #ddd;
      text-align: left;
    }
    th {
      background-color: #f2f2f2;
      font-weight: bold;
    }
    tr:hover {
      background-color: #f5f5f5;
    }
    .team-item {
      margin-bottom: 15px;
    }
    .team-name {
      font-weight: bold;
    }
    .team-seed {
      color: #555;
      margin-left: 5px;
    }
    .team-details {
      margin-left: 20px;
      font-size: 0.9em;
      color: #666;
    }
    .bracket-links {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 20px 0;
    }
    .bracket-link {
      display: inline-block;
      padding: 8px 15px;
      background-color: #0e4c92;
      color: white;
      text-decoration: none;
      border-radius: 4px;
      font-weight: bold;
      transition: background-color 0.3s;
    }
    .bracket-link:hover {
      background-color: #0a3a70;
    }
    .strengths {
      margin-top: 5px;
      font-style: italic;
      color: #555;
    }
    .tabs {
      display: flex;
      border-bottom: 1px solid #ddd;
      margin-bottom: 20px;
    }
    .tab {
      padding: 10px 20px;
      cursor: pointer;
      border: 1px solid transparent;
    }
    .tab.active {
      border: 1px solid #ddd;
      border-bottom-color: white;
      border-radius: 5px 5px 0 0;
      margin-bottom: -1px;
      background-color: white;
    }
    .tab-content {
      display: none;
    }
    .tab-content.active {
      display: block;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>NCAA Tournament Analysis Dashboard</h1>
    <p>Comprehensive analysis of teams, predictions, and tournament insights</p>
  </div>

  <div class="tabs">
    <div class="tab active" onclick="openTab(event, 'summary')">Summary</div>
    <div class="tab" onclick="openTab(event, 'cinderellas')">Cinderella Teams</div>
    <div class="tab" onclick="openTab(event, 'brackets')">Brackets</div>
    <div class="tab" onclick="openTab(event, 'rankings')">Team Rankings</div>
  </div>

  <div id="summary" class="tab-content active">
    <div class="container">
      <div class="card">
        <h2>Final Four Predictions</h2>
        ${generateFinalFourHTML(summary.consistentFinalFour)}
      </div>
      
      <div class="card">
        <h2>Championship Predictions</h2>
        ${generateChampionshipHTML(summary.consistentChampions)}
      </div>
    </div>
  </div>

  <div id="cinderellas" class="tab-content">
    <div class="card">
      <h2>Cinderella Teams Analysis</h2>
      ${summary.consistentCinderellas && summary.consistentCinderellas.length > 0 ? 
        generateCinderellasHTML(summary.consistentCinderellas) : 
        '<p>No consistent Cinderella teams found across bracket strategies</p>'}
      
      <h3>Top Ranked Potential Cinderellas</h3>
      ${generateRankingsTableHTML(cinderellaRankings, 10)}
    </div>
  </div>

  <div id="brackets" class="tab-content">
    <div class="card">
      <h2>Tournament Brackets</h2>
      <p>View different bracket strategies based on team rankings and prediction models:</p>
      
      <div class="bracket-links">
        <a href="bracket_standard.html" class="bracket-link" target="_blank">Standard</a>
        <a href="bracket_favorites.html" class="bracket-link" target="_blank">Favorites</a>
        <a href="bracket_upsets.html" class="bracket-link" target="_blank">Upsets</a>
        <a href="bracket_analytics.html" class="bracket-link" target="_blank">Analytics</a>
        <a href="bracket_cinderella.html" class="bracket-link" target="_blank">Cinderella</a>
        <a href="bracket_physical.html" class="bracket-link" target="_blank">Physical</a>
        <a href="bracket_momentum.html" class="bracket-link" target="_blank">Momentum</a>
        <a href="bracket_experience.html" class="bracket-link" target="_blank">Experience</a>
      </div>
    </div>
  </div>

  <div id="rankings" class="tab-content">
    <div class="card">
      <h2>Team Rankings</h2>
      <p>Top 25 teams based on combined metrics:</p>
      ${generateRankingsTableHTML(defaultRankings, 25)}
    </div>
  </div>

  <script>
    function openTab(evt, tabName) {
      var i, tabContent, tabLinks;
      
      // Hide all tab content
      tabContent = document.getElementsByClassName("tab-content");
      for (i = 0; i < tabContent.length; i++) {
        tabContent[i].className = tabContent[i].className.replace(" active", "");
      }
      
      // Remove "active" class from all tabs
      tabLinks = document.getElementsByClassName("tab");
      for (i = 0; i < tabLinks.length; i++) {
        tabLinks[i].className = tabLinks[i].className.replace(" active", "");
      }
      
      // Show the current tab and add "active" class to the button that opened the tab
      document.getElementById(tabName).className += " active";
      evt.currentTarget.className += " active";
    }
  </script>
</body>
</html>`;

  // Write HTML file
  fs.writeFileSync('tournament_dashboard.html', html);
  console.log('NCAA Tournament Dashboard generated: tournament_dashboard.html');
  
  return 'tournament_dashboard.html';
}

/**
 * Generate HTML for Final Four predictions
 */
function generateFinalFourHTML(finalFourTeams) {
  if (!finalFourTeams || finalFourTeams.length === 0) {
    return '<p>No Final Four predictions available</p>';
  }
  
  let html = '<div class="team-list">';
  
  finalFourTeams.forEach(team => {
    html += `
      <div class="team-item">
        <div class="team-name">${team.team} <span class="team-seed">(${team.seed} seed)</span></div>
        <div class="team-details">
          <div>Selected in ${team.count} brackets</div>
          <div>Offensive Efficiency: ${parseFloat(team.adjO).toFixed(1)}</div>
          <div>Defensive Efficiency: ${parseFloat(team.adjD).toFixed(1)}</div>
        </div>
      </div>
    `;
  });
  
  html += '</div>';
  return html;
}

/**
 * Generate HTML for Championship predictions
 */
function generateChampionshipHTML(championTeams) {
  if (!championTeams || championTeams.length === 0) {
    return '<p>No Championship predictions available</p>';
  }
  
  let html = '<div class="team-list">';
  
  championTeams.forEach(team => {
    html += `
      <div class="team-item">
        <div class="team-name">${team.team} <span class="team-seed">(${team.seed} seed)</span></div>
        <div class="team-details">
          <div>Selected in ${team.count} brackets</div>
          <div>Offensive Efficiency: ${parseFloat(team.adjO).toFixed(1)}</div>
          <div>Defensive Efficiency: ${parseFloat(team.adjD).toFixed(1)}</div>
        </div>
      </div>
    `;
  });
  
  html += '</div>';
  return html;
}

/**
 * Generate HTML for Cinderella team analysis
 */
function generateCinderellasHTML(cinderellaTeams) {
  let html = '<div class="team-list">';
  
  cinderellaTeams.forEach(team => {
    html += `
      <div class="team-item">
        <div class="team-name">${team.team} <span class="team-seed">(${team.seed} seed)</span></div>
        <div class="team-details">
          <div>Selected in ${team.count} brackets</div>`;
          
    if (team.strengths && team.strengths.length > 0) {
      html += `<div class="strengths">Key strengths: ${team.strengths.slice(0, 5).join(", ")}</div>`;
    }
    
    html += `
        </div>
      </div>
    `;
  });
  
  html += '</div>';
  return html;
}

/**
 * Generate HTML table for team rankings
 */
function generateRankingsTableHTML(rankings, limit = 25) {
  if (!rankings || rankings.length === 0) {
    return '<p>No ranking data available</p>';
  }
  
  // Limit the number of teams shown
  const limitedRankings = rankings.slice(0, limit);
  
  let html = `
    <table>
      <thead>
        <tr>
          <th>Rank</th>
          <th>Team</th>
          <th>Seed</th>
          <th>Conference</th>
          <th>Score</th>
        </tr>
      </thead>
      <tbody>
  `;
  
  limitedRankings.forEach(team => {
    html += `
      <tr>
        <td>${team.Rank}</td>
        <td>${team.Team}</td>
        <td>${team.Seed}</td>
        <td>${team.Conference}</td>
        <td>${parseFloat(team.Calculated_Score).toFixed(1)}</td>
      </tr>
    `;
  });
  
  html += `
      </tbody>
    </table>
  `;
  
  return html;
}

/**
 * Helper function to read CSV files
 */
function readCSV(filename) {
  try {
    const data = fs.readFileSync(filename, 'utf8');
    const lines = data.split('\n');
    const headers = lines[0].split(',');
    
    const result = [];
    for (let i = 1; i < lines.length; i++) {
      if (lines[i].trim() === '') continue;
      
      const values = parseCSVLine(lines[i]);
      const obj = {};
      
      for (let j = 0; j < headers.length; j++) {
        obj[headers[j]] = values[j];
      }
      
      result.push(obj);
    }
    
    return result;
  } catch (error) {
    console.error(`Error reading CSV file ${filename}:`, error);
    return [];
  }
}

/**
 * Parse a CSV line properly, handling quoted fields with commas
 */
function parseCSVLine(line) {
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
  
  return values;
}

// Export the function for use in other modules
module.exports = {
  generateDashboard
};

// If run directly, generate the dashboard
if (require.main === module) {
  generateDashboard();
}