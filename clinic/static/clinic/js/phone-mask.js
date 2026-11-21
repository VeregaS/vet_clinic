const phoneInput = document.getElementById("phone-mask");
if (phoneInput && typeof IMask === "function") {
    IMask(phoneInput, { mask: "+{7} (000) 000-00-00" });
}
