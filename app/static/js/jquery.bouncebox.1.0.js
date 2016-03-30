(function($){

	/* The plugin extends the jQuery Core with four methods */

	/* Converting an element into a bounce box: */
	$.fn.bounceBox = function(){

		/*
			Applying some CSS rules that center the
			element in the middle of the page and
			move it above the view area of the browser.
		*/

		this.css({
			top			: -(this.outerHeight()+20),
			marginLeft	: -this.outerWidth()/2,
			position	: 'fixed',
			left		: '50%'
		});

		return this;
	}

	/* The boxShow method */
	$.fn.bounceBoxShow = function(){

		/* Starting a downward animation */

		this.animate({top:0},{easing:'easeOutBack'});
		this.data('bounceShown',true);
		return this;
	}

	/* The boxHide method */
	$.fn.bounceBoxHide = function(){

		/* Starting an upward animation */

		this.animate({top:-this.outerHeight()},{easing:'easeInBack'});
		this.data('bounceShown',false);
		return this;
	}

	/* And the boxToggle method */
	$.fn.bounceBoxToggle = function(){

		/*
			Show or hide the bounceBox depending
			on the 'bounceShown' data variable
		*/

		if(this.data('bounceShown'))
			this.bounceBoxHide();
		else
			this.bounceBoxShow();

		return this;
	}

})(jQuery);