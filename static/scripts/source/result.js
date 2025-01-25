function hookEventListeners() {
  const productDetailsToggles = document.querySelectorAll(".details-toggle");
  let productId = 0;
  for (const productDetailToggle of productDetailsToggles) {
    productDetailToggle.addEventListener("click", (event) => {
      productId = productDetailToggle.getAttribute("product-id");
      fetchMoreInfo(productId);
    });
  }
}

async function fetchMoreInfo(productId) {
  const detailsDiv = document.getElementById(`product-details-${productId}`);
  const infoParagraph = document.getElementById(`additional-info-${productId}`);

  if (detailsDiv.style.display === "none") {
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
