// Elementos do DOM
const chatWindow = document.getElementById('chat-window');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');

// Variáveis para controlar o estado do chat
let isWaitingForResponse = false;

// Função para enviar mensagem
async function sendMessage() {
  const message = userInput.value.trim();
  
  // Verificar se a mensagem está vazia ou se já está a aguardar resposta
  if (!message || isWaitingForResponse) return;
  
  // Limpar o input e focar nele
  userInput.value = '';
  userInput.focus();
  
  // Adicionar a mensagem do utilizador ao chat
  addUserMessage(message);
  
  // Indicar que está a aguardar resposta
  isWaitingForResponse = true;
  
  try {
    // Mostrar indicador de digitação
    showTypingIndicator();
    
    // Enviar a mensagem para o servidor
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message })
    });
    
    // Verificar se a resposta foi bem-sucedida
    if (!response.ok) {
      throw new Error('Erro na comunicação com o servidor');
    }
    
    // Obter a resposta do servidor
    const data = await response.json();
    
    // Remover o indicador de digitação
    removeTypingIndicator();
    
    // Adicionar a resposta do chatbot ao chat
    addBotMessage(data.reply);
  } catch (error) {
    console.error('Erro:', error);
    
    // Remover o indicador de digitação
    removeTypingIndicator();
    
    // Mostrar mensagem de erro
    addBotMessage('Desculpa, ocorreu um erro ao processar a tua mensagem. Por favor, tenta novamente mais tarde.');
  } finally {
    // Indicar que já não está a aguardar resposta
    isWaitingForResponse = false;
  }
}

// Função para adicionar mensagem do utilizador ao chat
function addUserMessage(message) {
  const messageElement = document.createElement('div');
  messageElement.className = 'message user';
  
  const avatarElement = document.createElement('div');
  avatarElement.className = 'avatar';
  avatarElement.textContent = 'U';
  
  const contentElement = document.createElement('div');
  contentElement.className = 'content';
  contentElement.textContent = message;
  
  messageElement.appendChild(avatarElement);
  messageElement.appendChild(contentElement);
  
  chatWindow.appendChild(messageElement);
  
  // Scroll para o fundo do chat
  scrollToBottom();
}

// Função para adicionar mensagem do chatbot ao chat
function addBotMessage(message) {
  const messageElement = document.createElement('div');
  messageElement.className = 'message chatbot';

  const avatarElement = document.createElement('div');
  avatarElement.className = 'avatar';

  const avatarImg = document.createElement('img');
  avatarImg.src = 'mirobaldo_chatbot.png';
  avatarImg.alt = 'Chatbot Farense';

  avatarElement.appendChild(avatarImg);

  const contentElement = document.createElement('div');
  contentElement.className = 'content';
  // Use innerHTML to render Markdown/HTML content (biography content)
  // This allows images and formatted text to display properly
  contentElement.innerHTML = message;

  messageElement.appendChild(avatarElement);
  messageElement.appendChild(contentElement);

  chatWindow.appendChild(messageElement);

  // Scroll para o fundo do chat
  scrollToBottom();
}

// Função para mostrar indicador de digitação
function showTypingIndicator() {
  const typingElement = document.createElement('div');
  typingElement.className = 'message chatbot typing';
  typingElement.id = 'typing-indicator';
  
  const avatarElement = document.createElement('div');
  avatarElement.className = 'avatar';
  
  const avatarImg = document.createElement('img');
  avatarImg.src = 'mirobaldo_chatbot.png';
  avatarImg.alt = 'Chatbot Farense';
  
  avatarElement.appendChild(avatarImg);
  
  const contentElement = document.createElement('div');
  contentElement.className = 'content';
  contentElement.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  
  typingElement.appendChild(avatarElement);
  typingElement.appendChild(contentElement);
  
  chatWindow.appendChild(typingElement);
  
  // Scroll para o fundo do chat
  scrollToBottom();
}

// Função para remover indicador de digitação
function removeTypingIndicator() {
  const typingIndicator = document.getElementById('typing-indicator');
  if (typingIndicator) {
    typingIndicator.remove();
  }
}

// Função para fazer scroll para o fundo do chat
function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Ajustar a altura do textarea conforme o conteúdo
userInput.addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = (this.scrollHeight) + 'px';
  
  // Limitar a altura máxima
  if (this.scrollHeight > 150) {
    this.style.height = '150px';
    this.style.overflowY = 'auto';
  } else {
    this.style.overflowY = 'hidden';
  }
});

// Adicionar estilos para o indicador de digitação
const style = document.createElement('style');
style.textContent = `
  .typing .content {
    display: flex;
    align-items: center;
    min-width: 50px;
  }
  
  .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #fff;
    margin: 0 3px;
    opacity: 0.6;
    animation: dot-pulse 1.5s infinite ease-in-out;
  }
  
  .dot:nth-child(2) {
    animation-delay: 0.2s;
  }
  
  .dot:nth-child(3) {
    animation-delay: 0.4s;
  }
  
  @keyframes dot-pulse {
    0%, 100% {
      transform: scale(1);
      opacity: 0.6;
    }
    50% {
      transform: scale(1.2);
      opacity: 1;
    }
  }
`;
document.head.appendChild(style);

// Focar no input quando a página carrega
window.addEventListener('load', () => {
  userInput.focus();
}); 