//import * as areaChart from "./areaChart.js";
//import * as polarArea from "./polarArea.js";
import * as choroplethMap from "./choroplethMap.js";
//import * as anomalyRadial from "./anomalyRadial.js";

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


const firstYear = 2000; // b4 was 1901
const lastYear = 2020;
let country = "RUS";
let year = firstYear;
let month = 0;

// Init slider variables
const slider = document.getElementById("yearSlider");
slider.min = firstYear;
slider.max = lastYear;

// Init charts
/*areaChart.initChart("#areaChart");
polarArea.initChart("#polarArea");
anomalyRadial.initChart("#anomalyRadial");*/
choroplethMap.initChart("#choroplethMap");

// Datasets to load
const dataPromises = [
  d3.csv("data/temp-1901-2020-all.csv"),//0
  //d3.csv("data/HadCRUT4.csv"), //
  d3.json("data/world.geo.json"),//1
  d3.csv("data/disasters.csv"), //2
  d3.csv("data/twitterSection.csv"), // 3
  d3.csv("data/twitterSectionHydrated.csv"), // 4
];

//Disaster Type,Disaster Subtype,Disaster Group,Disaster Subgroup,Event Name,Origin,Country,Location,Latitude,Longitude,start_date,end_date,Total Deaths,No Affected,Reconstruction Costs ('000 US$),Total Damages ('000 US$),CPI
function isValid(disasterRow) {
  // Basic required fields check
  if (!disasterRow || !disasterRow.start_date || !disasterRow.Latitude || !disasterRow.Longitude) {
    return false;
  }

  // Parse and validate coordinates
  const lat = parseFloat(disasterRow.Latitude);
  const lng = parseFloat(disasterRow.Longitude);
  if (isNaN(lat) || isNaN(lng) || lat > 90 || lat < -90 || lng > 180 || lng < -180) {
    return false;
  }

  // Validate date
  const startDate = new Date(disasterRow.start_date);
  if (isNaN(startDate.getTime())) {
    return false;
  }

  return true;
}

//created_at,id,lng,lat,topic,sentiment,stance,gender,temperature_avg,aggressiveness
function isTValid(twitterRow) {
  if (twitterRow.lat >= 90 || twitterRow.lat <= -90 || twitterRow.lng >= 180 || twitterRow.lng <= -180)
    return false;
  
  if (!twitterRow["lat"] || !twitterRow["lng"])
    return false;

  //example of the built in javascript condition logic
      // if not null and no undefined and not empty string and not 0
          //if (twitterRow["lat"])  {   }
      // if null or undefined or empty string or 0
          //if (!twitterRow["lat"])  {   }

  return true;
}

function filterTweetsForDisaster(tweets, disaster) {
  if (!tweets || !disaster) return [];
  
  const disasterStart = new Date(disaster.start_date);
  const oneMonthBefore = new Date(disasterStart);
  oneMonthBefore.setMonth(disasterStart.getMonth() - 1);
  
  const oneMonthAfter = new Date(disasterStart);
  oneMonthAfter.setMonth(disasterStart.getMonth() + 1);

  return tweets.filter(tweet => {
    const tweetDate = new Date(tweet.created_at);
    return tweetDate >= oneMonthBefore && tweetDate <= oneMonthAfter;
  });
}

function convertRadiansToMiles(radians) {
  const earthRadiusInMiles = 3963;
  return radians * earthRadiusInMiles;
}

// Load datasets and start visualization
Promise.all(dataPromises).then(function (data) {
  const topoData = data[1];//topo data is world.geo.json
  // Group data per country and per year
  const tempData = d3.group(
    data[0],
    (d) => d.Year,
    (d) => d.ISO3 // Maybe change to country to be similar to disasters
  );
  /*const anomalyData = d3.group(
    data[1],
    (d) => d.Year
  );*/

  //data is all of csv files fetched from the server
  //data[0] is temp-1901-2020-all.csv
  //data[1] world.geo.json
  //data[2] disasters.csv

  //temp data array
  // for now, Lat and Long is a requirement. TODO: Either add disaster to center of country,
  // or find lat and long somehow
  var validData = [];
  for (var i = 0; i < data[2].length; i++) {
    if (isValid(data[2][i]) == true) {
      data[2][i].Year = new Date(data[2][i].start_date).getFullYear();
      data[2][i].Month = monthNames[new Date(data[2][i].start_date).getMonth()];
      if (data[2][i].Latitude && data[2][i].Longitude) {
        validData.push(data[2][i]);
      }
    }
  }
  data[2] = validData;
  
  const disastersData = d3.group(
    data[2],
    (d) => d.Year
  );

  //filter twitter data
  //created_at,               id,     lng,        lat,       topic,          sentiment,
  
  //2007-01-06 17:36:51+00:00,2266613,-73.9495823,40.6501038,Weather Extremes,-0.5678213599205018,
  
  //stance,gender,temperature_avg,aggressiveness
  //neutral,male,15.600876,aggressive
  var validTData = [];
  for (var i = 0; i < data[3].length; i++) {
    //if valid
    if (isTValid(data[3][i]) == true) {
      data[3][i].Year = new Date(data[3][i].created_at).getFullYear();
      data[3][i].Month = monthNames[new Date(data[3][i].created_at).getMonth() - 1];
      
      
      if (data[3][i].lat && data[3][i].lng) {
        validTData.push(data[3][i]);
      }
    } else {
      console.log("twitter row invalid")
      console.log(data[3][i]);
    }
  }
  data[3] = validTData;

  const twitterData = d3.group(
    data[3],
    (d) => d.Year,
  );

  //const twitterDataHydrated = d3.group(data[4])
  const twitterDataHydrated = data[4];

  //create a map object

  //loop through the data[4]

  // inside loop .set the key value pair

  // set twitterDataHydrated to map object

  
  var tweetsMap = new Map();

  for (var i = 0; i < twitterDataHydrated.length; i++) {
    // map.set(keys[i], values[i]); 
    tweetsMap.set(twitterDataHydrated[i].id, twitterDataHydrated[i].twitter_text);
  }
  
  // Maybe if the location of the tweet is close to the disaster the tweet is shown in the pop up.
  
  
  //before grouping
  //[{Disaster, 2007},{Disaster, 2007},{Disaster, 2008}]
  
  //after grouping
  //[{2007}: [0] Index X Axis
  // [{Disaster},{Disaster}] [0] Index Y Axis
  //[{2008}: [1] Index X Axis
  // [{Disaster}] [0] Index Y Axis

  //.get(2007)
  //[{Disaster},{Disaster}] [0] Index Y Axis
  
  //.get(2008)
  //[{Disaster}] [0] Index Y Axis
  
  // maybe loop through column and extract year using this thing.
  //const year = new Date(d.start_date).getFullYear();
  
  function updateCharts() {
    const yearData = tempData.get(String(year));
    const countryData = yearData.get(country);

    const dYearData = disastersData.get(year);
    const tYearData = twitterData.get(year);
    
    choroplethMap.updateChart(topoData, yearData, month, dYearData, tYearData, tweetsMap);
  }
  
  // original
  /*function updateCharts() {
    const yearData = tempData.get(String(year));
    const countryData = yearData.get(country);
    polarArea.updateChart(countryData);
    areaChart.updateChart(countryData);
    anomalyRadial.updateChart(anomalyData, year);
    choroplethMap.updateChart(topoData, yearData, month);
  } */
  updateCharts();
  //Animation
  let interval = d3.interval(() => {
    year = year < lastYear ? year + 1 : firstYear;
    slider.value = year;
    updateCharts();
    console.log(firstYear);
  }, 400);

  // UI
  // Slider
  let moving = false;
  slider.addEventListener("input", (event) => {
    if (moving) {
      interval.stop();
    }
    year = +slider.value;
    updateCharts();
  });
  slider.addEventListener("pointerup", (event) => {
    if (moving) {
      interval = d3.interval(() => {
        year = year < lastYear ? year + 1 : firstYear;
        slider.value = year;
        updateCharts();
      }, 400);
    }
  });
  // Play/pause button
  // document.getElementById('month-list').addEventListener();
  const playButton = d3.select("#play-button");
  playButton.on("click", function () {
    const button = d3.select(this);
    if (button.text() == "Pause") {
      moving = false;
      interval.stop();
      button.text("Play");
    } else {
      moving = true;
      interval = d3.interval(() => {
        year = year < lastYear ? year + 1 : firstYear;
        slider.value = year;
        updateCharts();
      }, 400);
      button.text("Pause");
    }
  });
  // Add month names to months drop down menu
  monthNames.forEach((month, i) => {
    document.getElementById(
      "month-list"
    ).innerHTML += `<li><a class="dropdown-item" value=${i}>${month}</a></li>`;
  });
  // Change months according to month menu
  document.querySelectorAll("#month-list li").forEach((item) =>
    item.addEventListener("click", (event) => {
      month = event.target.getAttribute("value");
      updateCharts();
    })
  );

  // Add years to years drop down menu
  for (let year of tempData.keys()) {
    document.getElementById(
      "year-list"
    ).innerHTML += `<li><a class="dropdown-item">${year}</a></li>`;
  }
  // Change year according to year menu
  document.querySelectorAll("#year-list li").forEach((item) =>
    item.addEventListener("click", (event) => {
      year = +event.target.innerHTML;
      slider.value = year;
      updateCharts();
    })
  );

  // Add countries to countries drop down menu
  for (let [iso, isoData] of tempData.get(String(firstYear))) {
    const countryName = isoData[0].Country;
    document.getElementById(
      "country-list"
    ).innerHTML += `<li><a class="dropdown-item" value=${iso}>${countryName}</a></li>`;
  }
  // Change country according to country menu
  document.querySelectorAll("#country-list li").forEach((item) =>
    item.addEventListener("click", (event) => {
      country = event.target.getAttribute("value");
      updateCharts();
    })
  );
});
