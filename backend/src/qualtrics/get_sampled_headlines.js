Qualtrics.SurveyEngine.addOnload(function() {
	this.hideNextButton();
	this.hidePreviousButton();
});

Qualtrics.SurveyEngine.addOnReady(function() {
	var user_id = Qualtrics.SurveyEngine.getEmbeddedData('userid');
	var wave = 1;
	var xmlHttp2 = new XMLHttpRequest();
	xmlHttp2.onreadystatechange = function() {
		if (xmlHttp2.readyState === 4 && xmlHttp2.status === 200){
			var response_text = xmlHttp2.responseText;
			Qualtrics.SurveyEngine.setEmbeddedData('PolFalse_1', response_text.split("$$$")[0]);
			Qualtrics.SurveyEngine.setEmbeddedData('PolTrue_1', response_text.split("$$$")[1]);
			Qualtrics.SurveyEngine.setEmbeddedData('PolFalse_2', response_text.split("$$$")[2]);
			Qualtrics.SurveyEngine.setEmbeddedData('PolTrue_2', response_text.split("$$$")[3]);

			jQuery('#NextButton').click();
		}
	}
	xmlHttp2.open("POST", 'https://nobbs.umd.edu/get_sampled_headlines?user_id='+user_id+'&wave='+wave, true);
	xmlHttp2.send(null);
});


Qualtrics.SurveyEngine.addOnUnload(function() {
  /* Place your JavaScript here to run when the page is unloaded */
});