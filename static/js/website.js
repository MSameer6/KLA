// ================================
// SCROLL TO TOP BUTTON
// ================================
const scrollTopButton = document.getElementById("scrollTop");

if (scrollTopButton) {
    window.addEventListener("scroll", function () {
        scrollTopButton.classList.toggle("show", window.scrollY > 300);
    });

    scrollTopButton.addEventListener("click", function () {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
}

// ================================
// MOBILE MENU
// ================================
const mobileMenu = document.getElementById("mobileMenu");
const navMenu = document.getElementById("navMenu");

if (mobileMenu && navMenu) {
    mobileMenu.addEventListener("click", function () {
        navMenu.classList.toggle("active");

        const icon = mobileMenu.querySelector("i");
        if (icon) {
            icon.classList.toggle("fa-bars", !navMenu.classList.contains("active"));
            icon.classList.toggle("fa-xmark", navMenu.classList.contains("active"));
        }
    });
}
