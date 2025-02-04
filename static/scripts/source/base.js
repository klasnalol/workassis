// On page load, set the dropdown to the saved language
document.addEventListener("DOMContentLoaded", function () {
  const savedLanguage = localStorage.getItem("selectedLanguage");
  if (savedLanguage) {
    document.getElementById("language").value = savedLanguage;
  }
});

// Event listener to save selected language
const dummy = document.createElement("template");
const language = document.getElementById("language");

(language || dummy).addEventListener("change", function () {
  const selectedLanguage = this.value;
  // Store the selected language in localStorage
  localStorage.setItem("selectedLanguage", selectedLanguage);
});

if(language === null){
    console.error(`Could not get an element with id "language"`);
}

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
