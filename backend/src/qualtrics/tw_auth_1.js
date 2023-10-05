Qualtrics.SurveyEngine.addOnload(function() {
  /* Place your JavaScript here to run when the page loads */
  this.hideNextButton();
  this.hidePreviousButton();
});

Qualtrics.SurveyEngine.addOnReady(function() {
  /*
    This function runs when the page is fully displayed.

    Step 1: Get a reference to the HTML element with id "twitter-login-btn".
    Step 2: Assign an onclick event handler to this element. When clicked, it will perform several actions.
            - It sends a GET request to the '/auth/' endpoint on server and retrieves an oauth_token.
            - Opens a popup window for Twitter OAuth authorization using obtained oauth_token.
            - If popup blocking prevents opening of new window, unhides an HTML element with id "popup".

    Step 3: Starts a polling mechanism that checks every second for up to 100 seconds:
            - If user successfully authorizes app in Twitter popup window,
              it sends another GET request to '/auth/getscreenname' endpoint on server with oauth_token as parameter,
              receives user's screen name, user ID and other related data from server response,
              sets these data into Qualtrics embedded data fields,
              then automatically clicks on next button in Qualtrics survey.

            - If any error occurs during this process or if count reaches maximum limit (100),
              it displays a failure message by unhiding an HTML element with id "fail".
   */

  var element = document.getElementById("twitter-login-btn");
  element.onclick = function(event) {
    var oauth_token_tt = "";
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.onreadystatechange = function() {
      if (xmlHttp.readyState === 4 && xmlHttp.status === 200) {
        // Use the obtained authorization URL from the response
        var authorizationUrl = xmlHttp.responseText;

        // Extract oauth_token from the response
       oauth_token_tt = xmlHttp.responseText;
		Qualtrics.SurveyEngine.setEmbeddedData( 'oauth_token', xmlHttp.responseText);
		let popup = window.open("https://api.twitter.com/oauth/authorize?oauth_token="+oauth_token_tt, "hello", "width=500,height=500");

        if (!popup)
          document.getElementById("popup").hidden = false;

        var count = 1;

        var pollTimer = window.setInterval(function() {
          count += 1;

          if (count === 100){
            window.clearInterval(pollTimer);
            document.getElementById("fail").hidden = false;
          }

          window.setTimeout(function() {
            var xmlHttp2 = new XMLHttpRequest();

            xmlHttp2.onreadystatechange = function() {
              if (xmlHttp2.readyState === 4 && xmlHttp2.status === 200){
                if (xmlHttp2.responseText !== "####") {
                  console.log(xmlHttp2.responseText);
                  if (popup)
                    popup.close();

                  window.clearInterval(pollTimer);

                  if (xmlHttp2.responseText === "error") {
                    document.getElementById("fail").hidden = false;
                  } else {
                    Qualtrics.SurveyEngine.setEmbeddedData( 'screename', xmlHttp2.responseText.split("$$$")[0]);
                    Qualtrics.SurveyEngine.setEmbeddedData( 'userid', xmlHttp2.responseText.split("$$$")[1]);
                    Qualtrics.SurveyEngine.setEmbeddedData( 'access_token', xmlHttp2.responseText.split("$$$")[2]);
                    Qualtrics.SurveyEngine.setEmbeddedData( 'access_token_secret', xmlHttp2.responseText.split("$$$")[3]);

                    setTimeout(function () { jQuery('#NextButton').click(); },200);

                  }
                }
              }
            }

			xmlHttp2.open("GET", 'https://nobbs.umd.edu/auth_screenname?oauth_token='+oauth_token_tt, true);
			xmlHttp2.send(null);
          }, 1);
        }, 1000);
      }
    }
    xmlHttp.open("GET", 'https://nobbs.umd.edu/auth/', true);
    xmlHttp.send(null);
  };
});

Qualtrics.SurveyEngine.addOnUnload(function() {
  /* Place your JavaScript here to run when the page is unloaded */
});