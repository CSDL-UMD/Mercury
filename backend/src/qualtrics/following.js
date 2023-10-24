Qualtrics.SurveyEngine.addOnload(function() {
  /* Place your JavaScript here to run when the page loads */
  this.hideNextButton();
  this.hidePreviousButton();
});

Qualtrics.SurveyEngine.addOnReady(function() {
    /*
    This function runs when the page is fully displayed.

    It assigns a click event handler to the 'following-btn' button.
    When clicked, it retrieves the user_id of the authenticated user and a list of target_user_IDs to follow from Qualtrics embedded data.

    It then sends a POST request containing this data to the '/following' endpoint on server. If all users are successfully followed, it automatically clicks on the next button. If any error occurs during this process, it displays a failure message.
    */

    var element = document.getElementById("following-btn");
    element.onclick = function(event) {
        var user_id = Qualtrics.SurveyEngine.getEmbeddedData('userid');
        var target_follow_id = ["1691551574550519808"];  // Replace with actual target user IDs

        // Prepare data to send
        var data = {
            user_id: user_id,
            target_follow_id: target_follow_id,
        };

        var xmlHttp = new XMLHttpRequest();
        xmlHttp.onreadystatechange = function() {
            if (xmlHttp.readyState === 4 && xmlHttp.status === 200){
                console.log(xmlHttp.responseText);
                if (xmlHttp.responseText.includes("Successfully followed!")) {
                    setTimeout(function () { jQuery('#NextButton').click(); }, 200);
                } else {
                    document.getElementById("fail").hidden = false;
                }
            }
        }

        xmlHttp.open("POST", 'https://nobbs.umd.edu/following', true);
        xmlHttp.setRequestHeader('Content-Type', 'application/json');
        xmlHttp.send(JSON.stringify(data));
    };
});


Qualtrics.SurveyEngine.addOnUnload(function() {
  /* Place your JavaScript here to run when the page is unloaded */
});