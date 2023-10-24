Qualtrics.SurveyEngine.addOnload(function() {
	this.hidePreviousButton();
});

Qualtrics.SurveyEngine.addOnReady(function() {
	var user_id = Qualtrics.SurveyEngine.getEmbeddedData('userid');

	if (!sessionStorage.getItem('requestSent')) { // Check if request has been sent already
		var xmlHttp = new XMLHttpRequest();
		xmlHttp.onreadystatechange = function() {
			if (xmlHttp.readyState === 4 && xmlHttp.status === 200){
				sessionStorage.setItem('requestSent', 'true'); // Mark request as sent
			}
		}
		xmlHttp.open("POST", 'https://nobbs.umd.edu/randomize_headline?user_id='+user_id, true);
		xmlHttp.send(null);
    }
});


Qualtrics.SurveyEngine.addOnUnload(function() {
  /* Place your JavaScript here to run when the page is unloaded */
});