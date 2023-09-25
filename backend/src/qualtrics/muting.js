Qualtrics.SurveyEngine.addOnload(function() {
  /* Place your JavaScript here to run when the page loads */
  this.hideNextButton();
  this.hidePreviousButton();
});

Qualtrics.SurveyEngine.addOnReady(function() {
    /*
    This function runs when the page is fully displayed.

    It assigns a click event handler to the 'muting-btn' button.
    When clicked, it retrieves the user_id of the authenticated user and a list of target_user_IDs to be muted from Qualtrics embedded data.

    It then sends a POST request containing this data to the '/muting' endpoint on server. If all users are successfully muted, it automatically clicks on the next button. If any error occurs during this process, it displays a failure message.
    */

    var element = document.getElementById("muting-btn");
    element.onclick = function(event) {
        var user_id = Qualtrics.SurveyEngine.getEmbeddedData('userid');
        var target_user_IDs = ["2421067430"];  // Replace with actual target user IDs

        // Prepare data to send
        var data = {
            user_id: user_id,
            target_user_IDs: target_user_IDs
        };

        var xmlHttp = new XMLHttpRequest();
        xmlHttp.onreadystatechange = function() {
            if (xmlHttp.readyState === 4 && xmlHttp.status === 200){
                console.log(xmlHttp.responseText);
                if (xmlHttp.responseText.includes("Muted")) {
                    setTimeout(function () { jQuery('#NextButton').click(); }, 200);
                } else {
                    document.getElementById("fail").hidden = false;
                }
            }
        }

        xmlHttp.open("POST", 'http://127.0.0.1:5000/muting', true);
        xmlHttp.setRequestHeader('Content-Type', 'application/json');
        xmlHttp.send(JSON.stringify(data));
    };
});


Qualtrics.SurveyEngine.addOnUnload(function() {
  /* Place your JavaScript here to run when the page is unloaded */
});