// SortTable - got it from andrew's pyndexer - no copyright included?
function makeSortable(theadrow, tbody) {
	tbody = document.getElementById(tbody);
	headrow = theadrow.cells;
	for (var i=0; i<headrow.length; i++) {
		if (headrow[i].getAttribute('sorttype') == 'numeric') {
			headrow[i].sortfunction = sort_numeric;
		} else {
			headrow[i].sortfunction = sort_alpha;
		}
		headrow[i].sortindex = i;
		headrow[i].sortbody = tbody;
		headrow[i]['onclick'] = sortTable;
		headrow[i].style['cursor'] = 'pointer';
	}
	showSort(tbody, headrow[0]);
}
function sortTable(e) {
	col = this.sortindex;
	tbody = this.sortbody;
	rows = tbody.rows;
	if (col == tbody.sortedcol) {
		// if we're already sorted by this column, just reverse the table
		for (var i=rows.length-1; i>=0; i--) {
			tbody.appendChild(rows[i]);
		}
		document.getElementById('sortindicator').innerHTML = tbody.sortedrev ? '&nbsp;&#x25BE;' : '&nbsp;&#x25B4;';
		tbody.sortedrev = !tbody.sortedrev;
		return;
	}
	// build an array to sort
	row_array = [];
	for (var j=0; j<rows.length; j++) {
		row_array[row_array.length] = [rows[j].cells[col].getAttribute('sortkey'), rows[j]];
	}
	row_array.sort(this.sortfunction);
	for (var j=0; j<row_array.length; j++) {
		tbody.appendChild(row_array[j][1]);
	}
	delete row_array;
	sortind = document.getElementById('sortindicator');
	if (sortind) { sortind.parentNode.removeChild(sortind); }
	showSort(tbody, this);
}
function showSort(tbody, headcell) {
	sortind = document.createElement('span');
	sortind.id = 'sortindicator';
	sortind.innerHTML = '&nbsp;&#x25BE;';
	headcell.appendChild(sortind);
	tbody.sortedcol = headcell.sortindex;
	tbody.sortedrev = false;
}
function sort_numeric(a,b) {
	return a[0]-b[0];
}
function sort_alpha(a,b) {
	if (a[0].toLowerCase()==b[0].toLowerCase()) return 0;
	if (a[0].toLowerCase()<b[0].toLowerCase()) return -1;
	return 1;
}
