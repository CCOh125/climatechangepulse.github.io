// Plot constants
const WIDTH = 1400;
const HEIGHT = 800;

// Helper functions - define these at the top level
function filterTweetsForDisaster(tweets, disaster) {
  if (!tweets || !disaster) return [];
  
  const disasterStart = new Date(disaster.start_date);
  
  // Increase time window to 6 months before and after
  const sixMonthsBefore = new Date(disasterStart);
  sixMonthsBefore.setMonth(disasterStart.getMonth() - 6);
  
  const sixMonthsAfter = new Date(disasterStart);
  sixMonthsAfter.setMonth(disasterStart.getMonth() + 6);

  console.log("Time window:", {
    start: sixMonthsBefore.toISOString(),
    disaster: disasterStart.toISOString(),
    end: sixMonthsAfter.toISOString()
  });

  // Filter and sort tweets by date (newest first)
  const filteredTweets = tweets.filter(tweet => {
    const tweetDate = new Date(tweet.created_at);
    return tweetDate >= sixMonthsBefore && tweetDate <= sixMonthsAfter;
  }).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  return filteredTweets;
}

function convertRadiansToMiles(radians) {
  const earthRadiusInMiles = 3963;
  return radians * earthRadiusInMiles;
}

let svg, g, g2, path, projection, colorScale, title, tooltip, disasterDetails, tipCountry, tipData, tipDisasterCountry, tipDisasterData;

let hovered = false;
let dhovered = false;

let tweetsElements = [];

const monthNames = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

// Create tweet container at the top level, outside any function
let tweetContainer = document.querySelector('.tweet-container');
if (!tweetContainer) {
  tweetContainer = document.createElement('div');
  tweetContainer.className = 'tweet-container';
  tweetContainer.style.position = 'fixed';
  tweetContainer.style.background = 'white';
  tweetContainer.style.padding = '20px';
  tweetContainer.style.borderRadius = '8px';
  tweetContainer.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
  tweetContainer.style.maxHeight = '80vh';
  tweetContainer.style.overflowY = 'auto';
  tweetContainer.style.display = 'none';
  tweetContainer.style.zIndex = '1000';
  document.body.appendChild(tweetContainer);
}

// Add click handler at top level
document.addEventListener('click', function(event) {
  const tweetContainer = document.querySelector('.tweet-container');
  if (tweetContainer && !event.target.closest('.tweet-container') && !event.target.closest('circle')) {
    tweetContainer.style.display = 'none';
  }
});

// Function to dynamically embed tweets
function embedTweets(tweets) {
  console.log("Attempting to embed tweets:", tweets);
  
  const tweetContainer = document.querySelector('.tweet-container');
  if (!tweetContainer) {
    console.error("Tweet container not found");
    return;
  }
  
  // Clear existing content
  tweetContainer.innerHTML = '';
  
  // Create a header with info about the tweets
  const header = document.createElement('div');
  header.style.marginBottom = '15px';
  header.style.padding = '10px';
  header.style.borderBottom = '1px solid #eee';
  header.innerHTML = `Found ${tweets.length} tweets from this time period`;
  tweetContainer.appendChild(header);
  
  // Take only the first 10 tweets
  const tweetsToShow = tweets.slice(0, 10);
  
  // Create a fallback display for tweets that can't be embedded
  tweetsToShow.forEach((tweet, index) => {
    const tweetDiv = document.createElement('div');
    tweetDiv.id = `tweet-${index}`;
    tweetDiv.style.marginBottom = '15px';
    tweetDiv.style.padding = '10px';
    tweetDiv.style.border = '1px solid #eee';
    tweetDiv.style.borderRadius = '5px';
    
    // Create fallback content
    const fallbackContent = document.createElement('div');
    fallbackContent.innerHTML = `
      <p style="margin: 0; color: #666;">Tweet ID: ${tweet.id_str || tweet.id}</p>
      <p style="margin: 5px 0;">${tweet.text || 'Tweet text not available'}</p>
      <p style="margin: 0; color: #666; font-size: 0.9em;">
        Posted on: ${new Date(tweet.created_at).toLocaleDateString()}
      </p>
    `;
    tweetDiv.appendChild(fallbackContent);
    tweetContainer.appendChild(tweetDiv);
    
    // Still try to embed, but don't rely on it
    twttr.widgets.createTweet(
      tweet.id_str || tweet.id,
      tweetDiv,
      {
        conversation: 'none',
        cards: 'hidden',
        align: 'center',
        theme: 'light'
      }
    ).then(function (el) {
      if (el) {
        console.log(`Successfully embedded tweet ${tweet.id_str || tweet.id}`);
        fallbackContent.style.display = 'none';
      } else {
        console.log(`Failed to embed tweet ${tweet.id_str || tweet.id}, using fallback`);
      }
    }).catch(error => {
      console.log(`Error embedding tweet ${tweet.id_str || tweet.id}, using fallback`);
    });
  });
  
  // Add a note about historical data
  if (tweets.some(tweet => new Date(tweet.created_at).getFullYear() < 2010)) {
    const note = document.createElement('div');
    note.style.marginTop = '15px';
    note.style.padding = '10px';
    note.style.backgroundColor = '#fff3cd';
    note.style.border = '1px solid #ffeeba';
    note.style.borderRadius = '5px';
    note.innerHTML = 'Note: Some older tweets may not be available for embedding due to Twitter\'s data retention policies.';
    tweetContainer.appendChild(note);
  }
}

function removeTweets() {
  const tweetContainer = document.getElementById('tweet-container');
  if (tweetContainer) {
    tweetContainer.innerHTML = '';
  }
}

function initChart(canvasElement) {
  // Initialize tweetsElements array
  tweetsElements = []; // Clear array first
  for (let i = 1; i <= 10; i++) {
    const element = document.getElementById(`tweet${i}`);
    if (element) {
      console.log(`Found tweet element ${i}`);
      tweetsElements.push(element);
    } else {
      console.log(`Missing tweet element ${i}`);
    }
  }
  
  // Get disaster details container
  disasterDetails = d3.select(".disasterDetails");
  console.log("Disaster details container found:", disasterDetails.node() !== null);

  // Visualization canvas
  svg = d3
    .select(canvasElement)
    .append("svg")
    .attr("width", WIDTH)
    .attr("height", HEIGHT);

  g = svg.append("g");

  g2 = svg.append("g");

  // Labels
  title = g
    .append("text")
    .attr("class", "x-label")
    .attr("x", WIDTH / 2)
    .attr("y", HEIGHT - 100)
    .attr("font-size", "20px")
    .attr("text-anchor", "middle");

  // Map and projection
  path = d3.geoPath();
  projection = d3
    .geoEqualEarth()
    .scale(250)
    .center([0, 0])
    .translate([WIDTH / 2, HEIGHT / 2]);

  colorScale = d3
    .scaleLinear()
    .domain([-30, 0, 35])
    .range(["#1788de", "#3C81B7", "#dc2f02"]);

  // Legend
  const legend = g
    .append("defs")
    .append("svg:linearGradient")
    .attr("id", "gradient")
    .attr("x1", "100%")
    .attr("y1", "0%")
    .attr("x2", "100%")
    .attr("y2", "100%")
    .attr("spreadMethod", "pad");

  legend
    .append("stop")
    .attr("offset", "0%")
    .attr("stop-color", "#dc2f02")
    .attr("stop-opacity", 1);

  legend
    .append("stop")
    .attr("offset", "100%")
    .attr("stop-color", "#3C81B7")
    .attr("stop-opacity", 1);

  const w = 110,
    h = 300;
  const y = d3.scaleLinear().domain([-30, 35]).range([h, 0]);
  g.append("rect")
    .attr("width", w - 100)
    .attr("height", h)
    .style("fill", "url(#gradient)")
    .attr("transform", "translate(0,200)");

  var yAxis = d3.axisRight(y).tickFormat((d) => d + "℃");

  g.append("g")
    .attr("class", "y axis")
    .attr("transform", "translate(10,200)")
    .call(yAxis);

  // Tooltip placeholder
  tooltip = d3.select(".tooltip");

  //handle the click event on the body tag
  //d3 has a select function d3.select(element)
  //element = "body"
  //select returns a selection object

  //use the object to call a on function

  //on function takes a string as an argument and a function as an argument

  d3.select("body")
    .on("click", function(event) {

      // when we click on a disaster, we don't want to fade out the popup
      //event.target = the element that was clicked on
      var clickedOn = event.target;

      // use d3.select and pass in event.target to get a selection object
      var selectedObj = d3.select(event.target);
      // if we clicked on a disaster, return
      if (selectedObj.classed("Disaster") == true)
        return;

      // did we click on an element that is inside of the disaster details div?
      // if we did, return
      if (disasterDetails.node().contains(event.target))
        return;


      // did we click on the disaster details div itself
      if (event.target == disasterDetails.node())
        return;

      // the selected object does not have a Disaster class on it
      // fade out the disaster details popup div
      disasterDetails.transition().duration(100).style("opacity", 0);
      disasterDetails.style("display", "none");
      // loop the the tweetsElements array
        // clear the html from each element
        // use the .html("")
      removeTweets();

      // dont fade out popup if we clicked on a disaster or on the disaster details
      // if the event.target is not the disaster details div
      // and if the event.target is not a disaster
      // then fade out the popup
      /*if (d3.select(event.target).classed("Disaster")) {
          console.log("Clicked on a disaster marker.");
          return;
        }

        if (disasterDetails.node().contains(event.target)) {
          console.log("Clicked inside the disaster details.");
          return;
        }

        if (event.target === disasterDetails.node()) {
          console.log("Clicked on the disaster details div.");
          return;
        }

        console.log("Fading out disaster details.");
        disasterDetails.transition().duration(100).style("opacity", 0);
        */
    });

}
//tHydrated = map object. map.get(id) == text
function updateChart(topo, data, month, dyear, tyear, tHydrated) {
  const trans = d3.transition().duration(100);
  
  // Get current year from data
  let currentYear;
  for (let [key, value] of data) {
    if (value && value[0] && value[0].Year) {
      currentYear = parseInt(value[0].Year);
      break;
    }
  }
  
  console.log("Current year:", currentYear);
  console.log("Raw disaster data:", dyear);

  // Update title with the year
  title.text(`${monthNames[month]}, ${currentYear}`);

  // Draw map
  const choroMap = g.selectAll("path").data(topo.features);
  choroMap.exit().remove();

  // Update map
  choroMap
    .enter()
    .append("path")
    .merge(choroMap)
    .attr("class", "Country")
    .transition(trans)
    .attr("d", path.projection(projection))
    .attr("fill", function(d) {
      d.total = data.get(d.properties["iso_a3"]);
      return d.total ? colorScale(d.total[month].Temperature) : 30;
    });

  // Remove existing disaster points
  g.selectAll("circle").remove();

  // Load disaster data if not provided
  if (!dyear && currentYear >= 2015 && currentYear <= 2020) {
    console.log("Loading disaster data for year:", currentYear);
    d3.csv("data/disasters.csv").then(function(disasters) {
      dyear = disasters.filter(d => {
        const disasterDate = new Date(d.start_date);
        return disasterDate.getFullYear() === currentYear;
      });
      console.log(`Loaded ${dyear.length} disasters for ${currentYear}`);
      
      // Debug the first few disasters
      console.log("Sample disasters:", dyear.slice(0, 3).map(d => ({
        date: d.start_date,
        lat: d.Latitude,
        lng: d.Longitude,
        type: d["Disaster Type"],
        country: d.Country
      })));
      
      renderDisasters(dyear);
    });
  } else {
    renderDisasters(dyear);
  }

  function renderDisasters(disasters) {
    if (!disasters) {
      console.log("No disaster data to render");
      return;
    }

    // Debug the data structure
    console.log("First disaster data structure:", disasters[0]);

    const validDisasters = disasters.filter(d => {
      // Check for alternate column names for coordinates
      const latitude = d.Latitude || d.latitude || d.LAT || d.lat;
      const longitude = d.Longitude || d.longitude || d.LONG || d.long || d.lng;
      
      const hasDate = !!d.start_date;
      const hasLong = !!longitude;
      const hasLat = !!latitude;
      const dateValid = !isNaN(new Date(d.start_date).getTime());
      const yearMatch = new Date(d.start_date).getFullYear() === currentYear;
      
      if (!hasDate || !hasLong || !hasLat || !dateValid || !yearMatch) {
        console.log("Invalid disaster:", {
          disaster: d,
          hasDate,
          hasLong,
          hasLat,
          dateValid,
          yearMatch,
          foundLat: latitude,
          foundLong: longitude,
          allKeys: Object.keys(d)
        });
      }
      
      // Store the found coordinates back in the disaster object
      if (hasLat && hasLong) {
        d.Latitude = latitude;
        d.Longitude = longitude;
      }
      
      return hasDate && hasLong && hasLat && dateValid && yearMatch;
    });

    console.log(`Valid disasters for ${currentYear}:`, validDisasters.length);
    
    if (validDisasters.length > 0) {
      console.log("Sample valid disaster:", validDisasters[0]);
    }

    const disasterMap = g.selectAll("circle")
      .data(validDisasters)
      .enter()
      .append("circle")
      .attr("class", "Disaster")
      .attr('r', '10px')
      .attr("transform", function(d) {
        return "translate(" + projection([parseFloat(d.Longitude), parseFloat(d.Latitude)]) + ")";
      })
      .style('fill', 'red')
      .style('cursor', 'pointer')
      .on("click", function(event, d) {
        event.stopPropagation();
        
        const tweetContainer = document.querySelector('.tweet-container');
        if (!tweetContainer) return;
        
        // Position the container near the click
        tweetContainer.style.left = (event.pageX + 20) + 'px';
        tweetContainer.style.top = (event.pageY) + 'px';
        tweetContainer.style.display = 'block';
        tweetContainer.innerHTML = '<div class="loading">Loading tweets...</div>';

        if (tyear) {
          const relevantTweets = filterTweetsForDisaster(tyear, d);
          console.log("Found relevant tweets:", relevantTweets.length);
          
          if (relevantTweets.length > 0) {
            embedTweets(relevantTweets);
          } else {
            tweetContainer.innerHTML = 'No tweets found for this disaster';
          }
        }
      });
  }

  // Interactivity
  choroMap
    .on("pointermove", function(event, d) {
      hovered = true;
      tipCountry = d.total ? d.total[0].ISO3 : null;
      tipData = tipCountry
        ? data.get(tipCountry)[month]
        : { Country: "No available data", Temperature: "" };
      tooltip.html(tipData.Country + "<br/>" + tipData.Temperature + "℃");
      tooltip
        .style("left", event.pageX + 10 + "px")
        .style("top", event.pageY - 28 + "px")
        .transition()
        .duration(100)
        .style("opacity", 0.9)
        .style("font-size", "10px");
      d3.selectAll(".Country").transition().duration(50).style("opacity", 0.5);
      d3.select(this)
        .transition()
        .duration(50)
        .style("opacity", 1)
        .style("stroke", "#0A0A0A")
        .style("stroke-width", "0.5px");
    })
    .on("pointerleave", function(event) {
      hovered = false;
      // Country highlighting
      d3.selectAll(".Country").transition().duration(50).style("opacity", 1);
      d3.select(this).transition().duration(50).style("stroke", "none");
      // Tooltip
      tooltip.transition().duration(100).style("opacity", 0);
    });
  // Update tooltip data
  if (hovered) {
    tipData = tipCountry
      ? data.get(tipCountry)[month]
      : { Country: "No available data", Temperature: "" };
    tooltip.html(tipData.Country + "<br/>" + tipData.Temperature + "℃");
  }
}

export { initChart, updateChart };

// Add CSS to your stylesheet or in a style tag
const style = document.createElement('style');
style.textContent = `
  .tweet-container {
    min-width: 300px;
    max-width: 550px;
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    max-height: 80vh;
    overflow-y: auto;
  }
  
  .loading {
    color: #666;
    font-style: italic;
    text-align: center;
    padding: 20px;
  }
`;
document.head.appendChild(style);
