// Sidebar logic
const openSearchBtn = document.getElementById("open-search-sidebar");
const closeSearchBtn = document.getElementById("close-search-sidebar");
const searchSidebar = document.getElementById("search-sidebar");

openSearchBtn.addEventListener("click", () => {
  searchSidebar.classList.add("open");
});

closeSearchBtn.addEventListener("click", () => {
  searchSidebar.classList.remove("open");
});

// Infinite Scrolling
let page = 2;
let isLoading = false;

window.addEventListener("scroll", () => {
  if (
    window.innerHeight + window.scrollY >= document.body.offsetHeight - 100 &&
    !isLoading
  ) {
    loadMoreProducts();
  }
});

async function loadMoreProducts() {
  try {
    isLoading = true;
    const response = await fetch(`/load_more_products?page=${page}`);
    if (!response.ok) throw new Error("Failed to fetch products.");

    const products = await response.json();

    if (products.length === 0) {
      return;
    }

    const container = document.getElementById("products-container");
    products.forEach((product) => {
      const productDiv = document.createElement("div");
      productDiv.className = "product-item";
      productDiv.innerHTML = `<div class="product-image"><img src="${product.image_url}" alt="${product.name}" /></div><button class="details-toggle" onclick="toggleDetails(this)">{{ translations['more_info'] }}</button><div class="product-details"><button type="button" class="less-info-btn" onclick="closeDetails(this)">{{ translations['less_info'] }}</button><h3>${product.name}</h3><p>${product.description}</p><p>Price: $${product.price}</p><p>Category: ${product.category}</p></div>`;
      container.appendChild(productDiv);
    });

    page += 1;
  } catch (error) {
    console.error("Error loading products:", error);
  } finally {
    isLoading = false;
  }
}

// Toggle Product Details with More Info button
function toggleDetails(button) {
  const details = button.nextElementSibling;
  const isOpen = details.classList.toggle("open");
  button.textContent = isOpen ? "Less Info" : "More Info";
}

// Close Product Details with Less Info button
function closeDetails(btn) {
  const details = btn.closest(".product-details");
  const item = details.closest(".product-item");
  const toggleBtn = item.querySelector(".details-toggle");
  details.classList.remove("open");
  toggleBtn.textContent = "More Info";
}

// On-Screen Keyboard Logic
document.addEventListener("DOMContentLoaded", () => {
  const keyboardContainer = document.getElementById("keyboard-container");
  const keyboard = document.getElementById("keyboard");
  const inputField = document.getElementById("query-input");
  const submitSearch = document.getElementById("submit-search");
  let isUppercase = false;

  const rows = [
    ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
    ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
    ["⇧", "z", "x", "c", "v", "b", "n", "m", "⌫"],
    ["Space", "Enter"],
  ];

  // Generate keyboard rows
  rows.forEach((row) => {
    const rowDiv = document.createElement("div");
    rowDiv.className = "keyboard-row";

    row.forEach((char) => {
      const key = document.createElement("button");
      key.type = "button";
      key.textContent = char === "Space" ? "Space" : char;
      key.className = `keyboard-key ${["⌫", "⇧", "Space", "Enter"].includes(char) ? "special-key" : ""}`;

      if (char === "⌫") {
        key.onclick = () => {
          inputField.value = inputField.value.slice(0, -1);
        };
      } else if (char === "⇧") {
        key.onclick = () => toggleUppercase();
      } else if (char === "Space") {
        key.onclick = () => {
          inputField.value += " ";
        };
        key.classList.add("space-bar");
      } else if (char === "Enter") {
        key.onclick = () => {
          if (inputField.value.trim() !== "") {
            submitSearch.click();
          }
        };
      } else {
        key.onclick = () => {
          inputField.value += isUppercase
            ? char.toUpperCase()
            : char.toLowerCase();
        };
      }

      rowDiv.appendChild(key);
    });
    keyboard.appendChild(rowDiv);
  });

  document.getElementById("keyboard-btn").addEventListener("click", () => {
    keyboardContainer.style.display = "flex";
  });

  window.closeKeyboard = () => {
    keyboardContainer.style.display = "none";
  };

  function toggleUppercase() {
    isUppercase = !isUppercase;
    const keys = document.querySelectorAll(".keyboard-key:not(.special-key)");
    keys.forEach((key) => {
      if (key.textContent !== "Space") {
        key.textContent = isUppercase
          ? key.textContent.toUpperCase()
          : key.textContent.toLowerCase();
      }
    });
  }
});
/* Script separation */
let mediaRecorderVoice, mediaRecorderReturn;
let recordedChunksVoice = [];
let recordedChunksReturn = [];

const micSelectVoice = document.getElementById("mic-select-voice");
const micSelectReturn = document.getElementById("mic-select-return");
const startBtnVoice = document.getElementById("start-record-btn-voice");
const stopBtnVoice = document.getElementById("stop-record-btn-voice");
const startBtnReturn = document.getElementById("start-record-btn-return");
const stopBtnReturn = document.getElementById("stop-record-btn-return");
const formVoice = document.getElementById("voice-input-form");
const formReturn = document.getElementById("return-product-form");
const floatingMicBtn = document.getElementById("floating-mic-btn");

async function populateMicrophones() {
  const devices = await navigator.mediaDevices.enumerateDevices();
  const audioInputs = devices.filter((d) => d.kind === "audioinput");

  micSelectVoice.innerHTML = "";
  micSelectReturn.innerHTML = "";

  audioInputs.forEach((device, index) => {
    const optionV = document.createElement("option");
    optionV.value = device.deviceId;
    optionV.textContent = device.label || `Microphone ${index + 1}`;
    micSelectVoice.appendChild(optionV);

    const optionR = document.createElement("option");
    optionR.value = device.deviceId;
    optionR.textContent = device.label || `Microphone ${index + 1}`;
    micSelectReturn.appendChild(optionR);
  });
}

// Populate microphones on load
populateMicrophones();

// Existing voice_input logic
startBtnVoice.addEventListener("click", async () => {
  recordedChunksVoice = [];
  const deviceId = micSelectVoice.value;
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { deviceId: deviceId ? { exact: deviceId } : undefined },
  });
  mediaRecorderVoice = new MediaRecorder(stream);

  mediaRecorderVoice.ondataavailable = (event) => {
    recordedChunksVoice.push(event.data);
  };

  mediaRecorderVoice.onstop = async () => {
    const audioBlob = new Blob(recordedChunksVoice, { type: "audio/webm" });
    const formData = new FormData(formVoice);
    formData.append("audio_file", audioBlob, "voice_input.webm");
    try {
      const response = await fetch(formVoice.action, {
        method: "POST",
        body: formData,
      });
      if (response.ok) {
        const resultHtml = await response.text();
        document.open();
        document.write(resultHtml);
        document.close();
      } else {
        console.error("Failed to submit audio.");
        alert("Failed to submit audio. Please try again.");
      }
    } catch (error) {
      console.error("Error submitting audio:", error);
      alert("Error submitting audio. Please try again.");
    }
  };

  mediaRecorderVoice.start();
  startBtnVoice.disabled = true;
  stopBtnVoice.disabled = false;

  // Automatically stop after 5 seconds
  setTimeout(() => {
    if (mediaRecorderVoice && mediaRecorderVoice.state !== "inactive") {
      mediaRecorderVoice.stop();
      startBtnVoice.disabled = false;
      stopBtnVoice.disabled = true;
    }
  }, 5000);
});

stopBtnVoice.addEventListener("click", () => {
  if (mediaRecorderVoice && mediaRecorderVoice.state !== "inactive") {
    mediaRecorderVoice.stop();
    startBtnVoice.disabled = false;
    stopBtnVoice.disabled = true;
  }
});

// For return_product
startBtnReturn.addEventListener("click", async () => {
  recordedChunksReturn = [];
  const deviceId = micSelectReturn.value;
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { deviceId: deviceId ? { exact: deviceId } : undefined },
  });
  mediaRecorderReturn = new MediaRecorder(stream);

  mediaRecorderReturn.ondataavailable = (event) => {
    recordedChunksReturn.push(event.data);
  };

  mediaRecorderReturn.onstop = async () => {
    const audioBlob = new Blob(recordedChunksReturn, { type: "audio/webm" });
    const formData = new FormData(formReturn);
    formData.append("audio_file", audioBlob, "voice_input.webm");
    try {
      const response = await fetch(formReturn.action, {
        method: "POST",
        body: formData,
      });
      if (response.ok) {
        const resultHtml = await response.text();
        document.open();
        document.write(resultHtml);
        document.close();
      } else {
        console.error("Failed to submit audio.");
      }
    } catch (error) {
      console.error("Error submitting audio:", error);
      alert("Error submitting audio. Please try again.");
    }
    hideRecordingAnimation();
  };
  showRecordingAnimation();
  mediaRecorderReturn.start();
  startBtnReturn.disabled = true;
  stopBtnReturn.disabled = false;

  // Automatically stop after 5 seconds
  setTimeout(() => {
    if (mediaRecorderReturn && mediaRecorderReturn.state !== "inactive") {
      mediaRecorderReturn.stop();
      startBtnReturn.disabled = false;
      stopBtnReturn.disabled = true;
    }
  }, 5000);
});

stopBtnReturn.addEventListener("click", () => {
  if (mediaRecorderReturn && mediaRecorderReturn.state !== "inactive") {
    mediaRecorderReturn.stop();
    startBtnReturn.disabled = false;
    stopBtnReturn.disabled = true;
  }
});

function showRecordingAnimation() {
  $("#recording-animation").removeClass("d-none");
}

function hideRecordingAnimation() {
  $("#recording-animation").addClass("d-none");
}
