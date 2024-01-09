Qualtrics.SurveyEngine.addOnload(function()
{
	/*
	This function runs when the page loads.

	Step 1: Retrieve 'screename' from Qualtrics embedded data and set it as the value of HTML element with id "screenameinput".
         	Also disable this input field to prevent user from changing it.

  	Step 2: Hide the 'Next' and 'Previous' buttons on the Qualtrics survey.

  	Step 3: Assign a click event handler to question choices. When a choice is clicked, it will perform several actions:
  		- If choice with id '4' is selected,
  			- show the 'Next' button and hide any previously displayed failure message (HTML element with id "incorrect").
        - If choice with id '5' is selected,
        	- show a failure message by unhiding an HTML element with id "incorrect", hide 'Next' and show 'Previous' button.
   */

	document.getElementById("screenameinput").value = "${e://Field/screename}";
	document.getElementById("screenameinput").disabled = true;
	this.hideNextButton();
	this.hidePreviousButton();
	var that = this;
    this.questionclick = function(event,element) {
		var choice = that.getSelectedChoices()[0];
		console.log(choice);
		if (choice == 4){
			console.log("choice1");
			jQuery("#NextButton").show();
			this.hidePreviousButton();
			document.getElementById("incorrect").hidden = true;
		}
		else if (choice == 5){
			this.hideNextButton();
			this.showPreviousButton();
			document.getElementById("incorrect").hidden = false;
		}
	}
});
Qualtrics.SurveyEngine.addOnReady(function()
{
	/*Place your JavaScript here to run when the page is fully displayed*/
});
Qualtrics.SurveyEngine.addOnUnload(function()
{
	/*Place your JavaScript here to run when the page is unloaded*/
});