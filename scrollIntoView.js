function scrollToView (id) {
	var elem = document.getElementById(id);
	if (!elem) {
		console.log("Could not find current line");
		return;
	}
	console.log(elem);
	var bounding = elem.getBoundingClientRect()
	var inView = (
		bounding.top >= 0 &&
		bounding.left >= 0 &&
		bounding.right <= (window.innerWidth || document.documentElement.clientWidth) &&
		bounding.bottom <= (window.innerHeight || document.documentElement.clientHeight)
	);

	if (!inView) {
		elem.scrollIntoView()
	}
}
