// Desabilitar pinch-to-zoom e impedir zoom acidental
document.addEventListener('touchmove', (e) => {
    if (e.touches.length > 1) {
        e.preventDefault();
    }
}, { passive: false });

document.addEventListener('gesturestart', (e) => {
    e.preventDefault();
});

// Desabilitar duplo-clique para zoom
let lastTouchEnd = 0;
document.addEventListener('touchend', (e) => {
    const now = Date.now();
    if (now - lastTouchEnd <= 300) {
        e.preventDefault();
    }
    lastTouchEnd = now;
}, false);

document.addEventListener('DOMContentLoaded', () => {
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const chatHistory = document.getElementById('chat-history');
    const quickActionBtns = document.querySelectorAll('.quick-action-btn');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');

    let currentChatId = null; // ID da conversa atual

    // Sidebar Toggle Functionality
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('visible');
            sidebarToggle.classList.toggle('open');
            const isExpanded = sidebar.classList.contains('visible');
            sidebarToggle.setAttribute('aria-expanded', isExpanded);
        });

        // Close sidebar when clicking on a history item
        chatHistory.addEventListener('click', () => {
            sidebar.classList.remove('visible');
            sidebarToggle.classList.remove('open');
            sidebarToggle.setAttribute('aria-expanded', 'false');
        });

        // Close sidebar when clicking outside
        document.addEventListener('click', (e) => {
            if (!sidebar.contains(e.target) && e.target !== sidebarToggle && !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove('visible');
                sidebarToggle.classList.remove('open');
                sidebarToggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    // Função para esconder o welcome screen
    function hideWelcomeScreen() {
        const welcomeScreen = document.querySelector('.welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.style.display = 'none';
        }
    }

    // Função para adicionar mensagem (renderização rápida de HTML pré-renderizado no servidor)
    function addMessage(sender, text) {
        hideWelcomeScreen();
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', sender);

        if (sender === 'bot') {
            // Servidor já envia HTML renderizado, basta colocar direto
            // Isso é muito mais rápido que fazer parsing no cliente
            messageElement.innerHTML = text;
            console.log('✅ Bot message inserted as HTML');
            console.log('HTML content:', text.substring(0, 200));
        } else {
            messageElement.textContent = text;
            console.log('✅ User message inserted as text');
        }

        // Batch DOM operations - add to document only once
        chatMessages.appendChild(messageElement);

        // Use requestAnimationFrame to defer scroll to next paint
        requestAnimationFrame(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }

    // Quick Actions - Adicionar event listeners
    quickActionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.getAttribute('data-query');
            if (query) {
                userInput.value = query;
                sendMessage();
            }
        });
    });

    // Função para carregar o histórico de conversas
    async function loadChatHistory() {
        chatHistory.innerHTML = ''; // Limpa o histórico atual
        try {
            const response = await fetch('/api/history'); // Endpoint para buscar o histórico
            const history = await response.json();

            history.forEach(chat => {
                const listItem = document.createElement('li');
                listItem.textContent = chat.title || `Chat ${chat.id}`; // Exibe título ou ID
                listItem.dataset.chatId = chat.id;
                listItem.addEventListener('click', () => selectChat(chat.id));
                chatHistory.appendChild(listItem);
            });
        } catch (error) {
            console.error('Erro ao carregar histórico de conversas:', error);
        }
    }

    // Função para selecionar uma conversa do histórico
    async function selectChat(chatId) {
        currentChatId = chatId;
        chatMessages.innerHTML = ''; // Limpa as mensagens atuais
        try {
            const response = await fetch(`/api/chat/${chatId}`); // Endpoint para buscar mensagens de um chat
            const chat = await response.json();

            chat.messages.forEach(msg => {
                addMessage(msg.sender, msg.text);
            });
        } catch (error) {
            console.error(`Erro ao carregar chat ${chatId}:`, error);
        }
    }

    // Função para enviar mensagem
    async function sendMessage() {
        const text = userInput.value.trim();
        if (text === '') return;

        addMessage('user', text);
        userInput.value = '';

        try {
            const response = await fetch('/api/chat', { // Endpoint para enviar mensagem
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: text, chatId: currentChatId }),
            });

            // Parse JSON de forma assíncrona para não bloquear o thread
            const responseText = await response.text();
            const data = JSON.parse(responseText);

            console.log('Resposta completa da API:', data); // Adicionado para depuração
            console.log('Resposta do bot (data.reply):', data.reply); // Adicionado para depuração
            addMessage('bot', data.reply); // Renderizar imediatamente sem efeito de digitação

            // Se for uma nova conversa, atualiza o histórico
            if (!currentChatId) {
                currentChatId = data.chatId;
                loadChatHistory();
            }
        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
            addMessage('bot', 'Desculpe, houve um erro ao processar sua mensagem.');
        }
    }

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Carrega o histórico de conversas ao iniciar
    loadChatHistory();
});