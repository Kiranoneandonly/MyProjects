
// 
// Collapsable Tbody Table Plugin
// 

(function($) {

	$.fn.collapsableTbody = function(opts) {
		opts = $.extend({ }, defaults, opts);

		return this.each(function() {
			var $table = $(this);

			// Init stuff ...

			// Set the click handler for expand/collapse
			$table.on('click.collapsableTbody', 'tbody tr:first-child', function() {
				var $tr = $(this);
				var $tbody = $tr.parent();

				// Grab the indicator element
				$indicator = $tr.find(opts.indicatorSelector);

				// Get all rows in this tbody other than the first one (the clicked one)
				var $trs = $tbody.find('tr:not(:first-child)');

				// Toggle the data attribute
				var action = ($tbody.data('collapsed') === 'yes') ? 'show': 'hide';
				$tbody.data('collapsed', (action === 'show') ? 'no' : 'yes');

				// Show/hide the rows
				$trs.animate(animationProperties(action), 300);

				// Change the indicator
				$indicator.html((action === 'show') ? opts.indicatorExpanded : opts.indicatorCollapsed);
			});
		});
	};

// -------------------------------------------------------------
	
	var defaults = {
		indicatorSelector: 'td.indicator',
		indicatorExpanded: '-',
		indicatorCollapsed: '+'
	};

// -------------------------------------------------------------
	
	function animationProperties(showHide) {
		return {
			opacity: showHide,
			height: showHide,
			paddingTop: showHide,
			paddingBottom: showHide
		};
	}

}(jQuery));