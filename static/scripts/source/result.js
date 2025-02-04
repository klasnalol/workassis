const dummyElement = document.createElement("dialog");

function checkIfNotNull(element, name, selector) {
  if (element !== null) {
    return;
  }
  console.error(`Could not find a ${name} by selector '${selector}'`);
}

function voiceFilterHook() {
  const startBtnVoice = document.querySelector("#start-record-btn-return");
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
}

function hookEventListeners() {
  const productDetailsToggles = document.querySelectorAll(".details-toggle");
  let productId = 0;
  for (const productDetailToggle of productDetailsToggles) {
    productDetailToggle.addEventListener("click", (event) => {
      productId = productDetailToggle.getAttribute("product-id");
      fetchMoreInfo(productId);
    });

    const filterButtonSelector = "#filter-button";
    /** @type {HTMLButtonElement | null} */
    const filterButton = document.querySelector(filterButtonSelector);
    const filterDialogSelector = "#filter-dialog";
    /** @type {HTMLDialogElement | null} */
    const filterDialog = document.querySelector(filterDialogSelector);
    checkIfNotNull(filterButton, "filter button", filterButtonSelector);
    checkIfNotNull(filterDialog, "dialog", filterDialogSelector);
    (filterButton || dummyElement).addEventListener("click", (event) => {
      (filterDialog || dummyElement).showModal();
    });
    // TODO: Implement voice filter
    const voiceFilterButtonSelector = "#voice-filter-button";
    const voiceFilterButton = document.querySelector(voiceFilterButtonSelector);
    checkIfNotNull(voiceFilterButton, "voice filter button", voiceFilterButtonSelector);
    const voiceFilterDialogSelector = "#voice-filter-dialog";
    const voiceFilterDialog = document.querySelector(voiceFilterDialogSelector);
    (voiceFilterButton || dummyElement).addEventListener("click", (event) => {
        voiceFilterDialog.showModal();
    });
    voiceFilterHook();
  }
}

async function fetchMoreInfo(productId) {
  const detailsDivSelector = `#product-details-${productId}`;
  const detailsDiv = document.querySelector(detailsDivSelector);
  const infoParagraphSelector = `#additional-info-${productId}`;
  const infoParagraph = document.getElementById(infoParagraphSelector);

  checkIfNotNull(detailsDivSelector, "details div", detailsDivSelector);
  checkIfNotNull(infoParagraph, "info paragraph", infoParagraphSelector);
  if ((detailsDiv || dummyElement).style.display === "none") {
    try {
      const response = await fetch(`/get_more_info/${productId}`);
      if (!response.ok) {
        throw new Error("Failed to fetch additional information.");
      }

      const data = await response.json();
      infoParagraph.textContent = data.additional_info;

      // Play the generated audio if available
      if (data.audio_url) {
        const audio = new Audio(data.audio_url);
        audio.play();
      }

      detailsDiv.style.display = "block";
    } catch (error) {
      console.error("Error fetching more info:", error);
    }
  } else {
    detailsDiv.style.display = "none";
  }
}

hookEventListeners();
