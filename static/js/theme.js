// Load saved theme
if (localStorage.getItem("theme") === "dark") {
    document.body.classList.add("bg-dark", "text-white");
}

// Toggle theme
function toggleTheme() {

    document.body.classList.toggle("bg-dark");
    document.body.classList.toggle("text-white");

    if (document.body.classList.contains("bg-dark")) {
        localStorage.setItem("theme", "dark");
    } else {
        localStorage.setItem("theme", "light");
    }

}