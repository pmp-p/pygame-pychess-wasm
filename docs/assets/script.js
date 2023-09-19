
    window.onscroll = function() {addRemoveSticky()};
var header = document.getElementById("header");
var sticky = header.offsetTop;
function addRemoveSticky() {
  if (window.pageYOffset > sticky) {
    header.classList.add("sticky");
  } else {
    header.classList.remove("sticky");
  }
} 

function openImagePopup(src) {
  var imagePopup = document.getElementById('image-popup');
  imagePopup.classList.add('image-popup-open');
  var imagePopupImg = document.getElementById('image-popup-img');
  imagePopupImg.src = src;
  var content = document.getElementById('content');
  content.style.filter = "blur(1px)";
}

function closeImagePopup() {
  var imagePopup = document.getElementById('image-popup');
  imagePopup.classList.remove('image-popup-open');
  var content = document.getElementById('content');
  content.style.filter = "none";
}
    