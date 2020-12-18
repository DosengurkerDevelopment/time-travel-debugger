bounding = document.getElementById("True-78").getBoundingClientRect()
if (
	bounding.top >= 0 &&
	bounding.left >= 0 &&
	bounding.right <= (window.innerWidth || document.documentElement.clientWidth) &&
	bounding.bottom <= (window.innerHeight || document.documentElement.clientHeight)
) {
	console.log('In the viewport!');
} else {
	console.log('Not in the viewport... whomp whomp');
}
