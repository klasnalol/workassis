// On page load, set the dropdown to the saved language
document.addEventListener("DOMContentLoaded", function () {
  const savedLanguage = localStorage.getItem("selectedLanguage");
  if (savedLanguage) {
    document.getElementById("language").value = savedLanguage;
  }
});

// Event listener to save selected language
document.getElementById("language").addEventListener("change", function () {
  const selectedLanguage = this.value;
  // Store the selected language in localStorage
  localStorage.setItem("selectedLanguage", selectedLanguage);
});

// Attach language to forms on submission
function attachLanguageToForms() {
  const language = localStorage.getItem("selectedLanguage") || "en";
  document.querySelectorAll("form").forEach((form) => {
    if (!form.querySelector('input[name="language"]')) {
      const languageInput = document.createElement("input");
      languageInput.type = "hidden";
      languageInput.name = "language";
      languageInput.value = language;
      form.appendChild(languageInput);
    }
  });
}

document.querySelectorAll("form").forEach((form) => {
  form.addEventListener("submit", attachLanguageToForms);
});
