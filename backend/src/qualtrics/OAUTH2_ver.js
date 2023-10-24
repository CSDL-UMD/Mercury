Qualtrics.SurveyEngine.addOnload(function() {
  /* Place your JavaScript here to run when the page loads */
  this.hideNextButton();
  this.hidePreviousButton();
});

Qualtrics.SurveyEngine.addOnReady(function() {
  /*
    This function runs when the page is fully displayed.
   */

  var element = document.getElementById("twitter-login-btn");
  element.onclick = function(event) {
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.onreadystatechange = function() {
      if (xmlHttp.readyState === 4 && xmlHttp.status === 200) {
        var link = xmlHttp.responseText; // return from /auth/: authorizationUrl + unique_id
        var parts = link.split("&unique_id=")
        var authorizationUrl = parts[0];
        var unique_id = parts[1];
        Qualtrics.SurveyEngine.setEmbeddedData('unique_id', unique_id);

        let popup = window.open(
            "https://nobbs.umd.edu/qualrender?unique_id="+unique_id+"&authorizationUrl="+encodeURIComponent(authorizationUrl),
            "hello", "width=500,height=500");

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

                    setTimeout(function () { jQuery('#NextButton').click(); },200);
                  }
                }
              }
            }

            xmlHttp2.open("GET", 'https://nobbs.umd.edu/auth_screenname?tokens='+unique_id,true);
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