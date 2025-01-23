document.addEventListener('DOMContentLoaded', function() {
    const chatBlock = document.getElementById('chat-block');
    const toggleBtn = document.getElementById('chat-toggle-btn');
  
    if (chatBlock && toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        chatBlock.classList.toggle('chat-open');
        chatBlock.classList.toggle('chat-closed');
      });
    }
  });
  