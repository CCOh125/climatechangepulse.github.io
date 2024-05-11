// Plot constants
const WIDTH = 1400;
const HEIGHT = 800;

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

// Function to dynamically embed tweets
function embedTweets(tweetIDs) {
  //tweetIDS can be from 0 to 10
  tweetIDs.forEach(function(id, index) {
      twttr.widgets.createTweet(
          id,
          //use the tweetsElements array instead of document.getElementById
          tweetsElements[index],
          {
              conversation : 'none',    // Options to not show replies
              cards        : 'hidden',  // Hides cards (images, polls, etc.)
              align        : 'center',  // Centers the tweet
              theme        : 'light'    // Use 'dark' for dark mode
          }
      );
  });
  
}

// if tweetIDs.length == 1
//loop through tweetIDs.length - 1 to 10
// getDocumentById()
//tweetsElements <- has document nodes
// document nodes have innerHTML on them
// innerHTML = "";

function removeTweets(tweetIDs) {
  //if length = 0 the start index would be -1 so create a case for an empty array
  // define a startIndex
  for (let i = 0; i < 10; i++) {
      tweetsElements[i].innerHTML = "";
  }
}

function initChart(canvasElement) {
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
  disasterDetails = d3.select(".disasterDetails");

  //loop from 0 to 9
    //d3.select("#tweet" + (index + 1));

  for (let i = 0; i < 10; i++) {
    //push to the tweetsElements array
    tweetsElements.push(document.getElementById("tweet" + (i + 1)))
  }
  //get a reference to the disaster details div

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
  const currentYear = data.values().next().value[0].Year;
  title.text(`${monthNames[month]}, ${currentYear}`);

  // Draw map
  // Join
  const choroMap = g.selectAll("path").data(topo.features);

  // Exit
  choroMap.exit().remove();



  // Update
  choroMap
    .enter()
    .append("path")
    .merge(choroMap)
    .attr("class", "Country")
    .transition(trans)
    // draw each country
    .attr("d", path.projection(projection))
    // set the color of each country
    .attr("fill", function(d) {
      d.total = data.get(d.properties["iso_a3"]);
      return d.total ? colorScale(d.total[month].Temperature) : 30;
    });



  /*if (dyear) {
    choroMap
    .enter()
    .append('circle')
    //.attr('cx', projection([-106.661513, 35.05917399])[0])
    //.attr('cy', projection([-106.661513, 35.05917399])[1])
    //.attr('cx', function(d) { return xScale(d.value); })
    .attr('r','10px')
    .attr('cx', projection([dyear.Latitude, dyear.Longitude])[0])
    .attr('cy', projection([dyear.Latitude, dyear.Longitude])[1])
    .style('fill', 'red');
  }*/
  g.selectAll("circle").remove().exit();
  if (dyear) {
    //clears disasters
    const disasterMap = g.selectAll("circle").data(dyear);
    disasterMap
      .enter()
      .data(dyear)
      .append('circle')
      .attr("class", "Disaster")
      .attr('r', '10px')
      .attr("transform", function(d) {
        return "translate(" + projection([
          d.Longitude,
          d.Latitude
        ]) + ")"
      })
      .style('fill', 'red')
      .on("mouseover", function(event, d) {
        //when mouse hovers circle
        //d is a disaster row from disaster.csv
        dhovered = true;
        tipDisasterCountry = d.Country;
        tipDisasterData = { // Creating a new object to avoid mutating the original object
          Country: d.Country,
          TotalDeaths: d['Total Deaths']
        };
        tooltip.html(tipDisasterData.Country + "<br/>" + "Total deaths:" + tipDisasterData.TotalDeaths);
        tooltip
          .style("left", event.pageX + 10 + "px")
          .style("top", event.pageY - 28 + "px")
          .transition()
          .duration(100)
          .style("opacity", 0.9)
          .style("font-size", "10px");
        d3.selectAll(".Disaster").transition().duration(50).style("opacity", 0.5);
        d3.select(this)
          .transition()
          .duration(50)
          .style("opacity", 1)
          .style("stroke", "#0A0A0A")
          .style("stroke-width", "0.5px");
      })
      .on("mouseout", function(d) {
        //when mouse exits circle
        dhovered = false;
        // fading out all disaster circles
        d3.selectAll(".Disaster").transition().duration(50).style("opacity", 1);
        // setting the stroke around the clicked on circle to none
        // this = clicked on circle
        d3.select(this).transition().duration(50).style("stroke", "none");
        // Tooltip
        tooltip.transition().duration(100).style("opacity", 0);
      })
      .on("click", function(event, d) {
        //event has details of the mouse click
        //what html element we clicked on
        //x, y coordinates of where we clicked
        //d is a disaster row from disaster.csv

        //fade out the tooltip
        tooltip.transition().duration(100).style("opacity", 0);

        /* copy of below code
        var disasterCoords = [d.Longitude, d.Latitude];
          var tweetCoords = [twitterData.lng, twitterData.lat];
          var distance = d3.geoDistance(disasterCoords, tweetCoords);
          return distance < 0.5*/

        /*function compareFn(a, b) {
          if (a is less than b by some ordering criterion) {
            return -1;
          } else if (a is greater than b by the ordering criterion) {
            return 1;
          }
          // a must be equal to b
          return 0;
        }*/

        //filter out all the tweets that are not close to the disaster
        if (tyear) {
          //create an array of tweets that are created within the disaster date and end date
          let tweetsDuringDisaster = tyear.filter(twitterData => {
            //calculate distance between tweet and disaster
            //if distance is less than 1 return true
            var created_at = new Date(twitterData.created_at);
            return (created_at >= new Date(d.start_date) && created_at <= new Date(d.end_date));
          });
          
          //maybe create a max count and filter out by some specification
          //sort by distance

          //var disasterCoords = [d.Longitude, d.Latitude];
          //var tweetCoords = [twitterData.lng, twitterData.lat];

          //var distance = d3.geoDistance(disasterCoords, tweetCoords);
          //var distanceKm = distanceRadians * R;
          //return distance < 0.5

          function convertRadiansToMiles(radians) {
              const earthRadiusInMiles = 3963; // Earth's radius in miles
              return radians * earthRadiusInMiles;
          }

          // loop through tweets and calculate the distance to the epicenter
          // set a variable on the tweet that is the distance to the epicenter
          var disasterEpicenter = [d.Longitude, d.Latitude];

          for (var i = 0; i < tweetsDuringDisaster.length; i++) {
            var tweetCoords = [tweetsDuringDisaster[i].lng, tweetsDuringDisaster[i].lat];
            tweetsDuringDisaster[i].distanceToDisaster = d3.geoDistance(tweetCoords, disasterEpicenter);
            tweetsDuringDisaster[i].distanceToDisasterInMiles = convertRadiansToMiles(tweetsDuringDisaster[i].distanceToDisaster);
          }

          tweetsDuringDisaster = tweetsDuringDisaster.filter(twitterData => {
            //filter out any tweets that have a distance in miles to the disaster greater than 500 miles
            // return true if the distance is less than or equal to miles
            
            return twitterData.distanceToDisasterInMiles <= 1000;
          });

          //compare a's distance to the epicenter of the disaster to the b's distance to the epicenter of the disaster

          function compareFn(tweetA, tweetB) {
            if (tweetA.distanceToDisaster < tweetB.distanceToDisaster) {
              return -1;
            } else if (tweetB.distanceToDisaster < tweetA.distanceToDisaster) {
              return 1;
            }
            // a must be equal to b
            return 0;
          }

          //tweets sorted by distance
          let sortedTweets = tweetsDuringDisaster.sort(compareFn);
          if (sortedTweets.length > 10)
            sortedTweets = sortedTweets.slice(0, 10)

          //code making sure only a certain # of disasters are shown
          

          
          //adding html to the disasters details popup
          let tweetIDS = [];
          for (var i = 0; i < sortedTweets.length; i++) {
            tweetIDS.push(sortedTweets[i].id);
          }
          //give embedTweets a list of tweetIDS

          removeTweets(tweetIDS);
          embedTweets(tweetIDS);
          
          //disasterDetails.html("Tweets that are during the disaster: " + tweets);
          console.log(sortedTweets)
        } else {
          // loop through the tweetsElements
            // set innerHTML = ""
          removeTweets();
          //disasterDetails.html("No avaliable data");
          //console.log(data[4]);
        }
        disasterDetails.style("display", "block");
        //fade in a popup that has details of the disaster
        disasterDetails
          .style("left", event.pageX + 10 + "px")
          .style("top", event.pageY - 28 + "px")
          .transition()
          .duration(100)
          .style("opacity", 1)
          .style("font-size", "10px");
      })
      ;
    

    // Update tooltip data
    if (dhovered) {
      //tipDisasterData = tipCountry ? data.get(tipCountry)[month] : {Country: "No available data", Temperature: ""};
      tooltip.html(tipDisasterData.Country + "<br/>" + "Total Deaths:" + tipDisasterData.TotalDeaths);
    }
  } else {
    g.selectAll("circle").remove();
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
