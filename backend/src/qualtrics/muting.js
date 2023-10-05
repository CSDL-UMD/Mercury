Qualtrics.SurveyEngine.addOnload(function() {
  /* Place your JavaScript here to run when the page is unloaded */
  this.hideNextButton();
  this.hidePreviousButton();
});

Qualtrics.SurveyEngine.addOnReady(function() {
    /*
    This function runs when the page is fully displayed.

    Step 1: Get a reference to the HTML element with id "muting-btn".
    Step 2: Assign an onclick event handler to this element. When clicked, it will perform several actions.
    Step 3: Retrieve 'userid' from Qualtrics embedded data. This user ID represents the authenticated Twitter user.
    Step 4: Define a list of target_user_IDs that represent users to be muted on Twitter.
            (Replace ["2421067430"] with actual target user IDs.)
    Step 5: Prepare data for sending by creating an object that includes 'user_id' and 'target_user_IDs'.

    The event handler then sends a POST request containing this data to the '/muting' endpoint on server:
        - If all users are successfully muted, it automatically clicks on the next button in Qualtrics survey
        - If any error occurs during this process, it displays a failure message by unhiding an HTML element with id "fail".
   */

   var element = document.getElementById("muting-btn");
   element.onclick = function(event) {
       var user_id = Qualtrics.SurveyEngine.getEmbeddedData('userid');
       var target_user_IDs = ["2421067430"]; // Replace with actual target user IDs

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
                   setTimeout(function () { jQuery('#NextButton').click(); },200);
               } else {
                   document.getElementById("fail").hidden = false;
               }
           }
        }

        xmlHttp.open("POST", 'https://nobbs.umd.edu/muting', true);
        xmlHttp.setRequestHeader('Content-Type', 'application/json');
        xmlHttp.send(JSON.stringify(data));
   };
});


Qualtrics.SurveyEngine.addOnUnload(function() {
 /* Place your JavaScript here to run when the page is unloaded */
});
