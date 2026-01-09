// Robust Modal Interaction Script
(function() {
    // Comprehensive error handling
    window.addEventListener('error', function(event) {
        console.error(' CRITICAL ERROR:', event);
        alert(`Critical Error: ${event.message}`);
    });

    // Wait for entire DOM to be fully loaded
    function initializeModalInteraction() {
        console.group(' Modal Interaction Initialization');
        
        // Multiple element selection strategies
        const startChatButton = 
            document.getElementById('start-chat-button') || 
            document.querySelector('#start-chat-button') || 
            document.getElementsByClassName('btn btn-primary')[0];

        const closeChatButton = 
            document.getElementById('close-chat-button') || 
            document.querySelector('#close-chat-button');

        const chatModal = 
            document.getElementById('chat-modal') || 
            document.querySelector('.chat-modal');

        // Detailed logging
        console.log('Start Chat Button:', startChatButton);
        console.log('Close Chat Button:', closeChatButton);
        console.log('Chat Modal:', chatModal);
        console.groupEnd();

        // Validation checks
        if (!startChatButton) {
            console.error(' START CHAT BUTTON NOT FOUND');
            alert('Error: Start Chat Button is Missing!');
            return;
        }

        if (!chatModal) {
            console.error(' CHAT MODAL NOT FOUND');
            alert('Error: Chat Modal is Missing!');
            return;
        }

        // Force initial modal state
        chatModal.style.display = 'none';
        chatModal.style.opacity = '0';
        chatModal.style.visibility = 'hidden';

        // Comprehensive modal toggle function
        function toggleModal(action = 'show') {
            console.log(` Attempting to ${action} modal`);
            
            try {
                if (action === 'show') {
                    chatModal.style.display = 'flex';
                    chatModal.style.opacity = '1';
                    chatModal.style.visibility = 'visible';
                    console.log(' Modal Opened Successfully');
                } else {
                    chatModal.style.display = 'none';
                    chatModal.style.opacity = '0';
                    chatModal.style.visibility = 'hidden';
                    console.log(' Modal Closed Successfully');
                }
            } catch (error) {
                console.error(' Modal Toggle Error:', error);
                alert(`Modal Toggle Error: ${error.message}`);
            }
        }

        // Event binding with multiple strategies
        function bindModalEvents() {
            // Start Chat Button Events
            ['click', 'touchstart'].forEach(eventType => {
                startChatButton.addEventListener(eventType, (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    toggleModal('show');
                });
            });

            // Close Button Events
            if (closeChatButton) {
                ['click', 'touchstart'].forEach(eventType => {
                    closeChatButton.addEventListener(eventType, (event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        toggleModal('hide');
                    });
                });
            }

            // Close modal when clicking outside
            chatModal.addEventListener('click', (event) => {
                if (event.target === chatModal) {
                    toggleModal('hide');
                }
            });
        }

        // Initialize event bindings
        bindModalEvents();

        console.log(' Modal Interaction Fully Initialized');
    }

    // Multiple load event strategies
    ['DOMContentLoaded', 'load'].forEach(eventType => {
        window.addEventListener(eventType, initializeModalInteraction);
    });
})();