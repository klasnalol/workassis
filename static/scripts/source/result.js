const dummyElement = document.createElement("dialog")

function checkIfNotNull(element, name, selector){
    if(element !== null){
        return;
    }
    console.error(`Could not find a ${name} by selector '${selector}'`);
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
    const filterDialogSelector = "#filter-dealog";
    /** @type {HTMLDialogElement | null} */
    const filterDialog = document.querySelector(filterDialogSelector);
    checkIfNotNull(filterButton, "filter button", filterButtonSelector);
    checkIfNotNull(filterDialog, "dialog", filterDialogSelector);
    (filterButton || dummyElement).addEventListener("click", (event) => {
        (filterDialog || dummyElement).showModal()
    });
  }
}

async function fetchMoreInfo(productId) {
  const detailsDivSelector = `#product-details-${productId}`;
  const detailsDiv = document.querySelector(detailsDivSelector) 
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
