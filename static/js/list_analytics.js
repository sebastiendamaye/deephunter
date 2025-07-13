$("#myTable").tablesorter()
 .bind("sortEnd",function(e, t) {
			$("#myTable .row-summary").each(function() {
			var $rowSummary = $(this)
		var rowIdentifer = $rowSummary.data('row-number')
		var $rowExpander = $("#myTable .row-expanded[data-row-number='" + rowIdentifer + "']")
		$rowSummary.after($rowExpander)
	})
});

$(".toggle-row").click(function() {
 // add in accordion - first close anything
//$("#myTable .row-summary .active").removeClass("active").closest("tr").next("tr").collapse("hide")

// make this one visible
$(this).toggleClass("active");
$(this).closest("tr").next("tr").collapse("toggle")

//.toggle();
})

$('.btn').click(function(){
	$("#d_"+this.id.split('_')[1]).load("/"+this.id.split('_')[1]+"/detail/");
});

/* remove filter button */
$('.button_filter').click(function(){
	$( "#"+this.id.split('_')[1]+this.id.split('_')[2] ).prop( "checked", false );
	$("#form1").submit();
	return false;
});

$(function(){
    $("#form1").change(function(){
        this.submit();
    });
});
