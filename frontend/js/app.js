/**
 * Lenny Growth Assistant — Core Application
 * Vanilla JavaScript (No React, No Frameworks, Clean & Modular)
 */

import { api, API_CONFIG } from './api.js';

// ==========================================
// Application State
// ==========================================

const state = {
  activeConversationId: null,
  activeView: 'chat', // 'chat' | 'knowledge-base'
  activeProvider: 'cloud', // 'ollama' | 'cloud'
  currentArtifact: null,
  artifactTab: 'preview', // 'preview' | 'code'
  isArtifactOpen: false,
  isStreaming: false,
  conversations: []
};

// ==========================================
// DOM Element Selectors
// ==========================================

const elements = {
  // Navigation & Shell
  sidebar: document.getElementById('sidebar'),
  drawerBackdrop: document.getElementById('drawer-backdrop'),
  btnMobileMenu: document.getElementById('btn-mobile-menu'),
  btnDesktopToggleSidebar: document.getElementById('btn-desktop-toggle-sidebar'),
  btnNewChat: document.getElementById('btn-new-chat'),
  historyToday: document.getElementById('history-today'),
  historyYesterday: document.getElementById('history-yesterday'),
  historyPrevious: document.getElementById('history-previous'),
  navKnowledgeBase: document.getElementById('nav-knowledge-base'),
  btnSidebarAddKb: document.getElementById('btn-sidebar-add-kb'),
  sidebarKbCount: document.getElementById('sidebar-kb-count'),
  navOpenArtifact: document.getElementById('nav-open-artifact'),
  sidebarArtifactStatus: document.getElementById('sidebar-artifact-status'),
  navSettings: document.getElementById('nav-settings'),
  topbarViewTitle: document.getElementById('topbar-view-title'),

  // Model Switching & Status
  tabModelOllama: document.getElementById('tab-model-ollama'),
  tabModelCloud: document.getElementById('tab-model-cloud'),
  providerStatusBadge: document.getElementById('provider-status-badge'),
  providerStatusDot: document.getElementById('provider-status-dot'),
  providerStatusText: document.getElementById('provider-status-text'),
  btnToggleArtifact: document.getElementById('btn-toggle-artifact'),
  btnMoreOptions: document.getElementById('btn-more-options'),

  // Chat View Elements
  chatPane: document.getElementById('chat-pane'),
  chatScrollArea: document.getElementById('chat-scroll-area'),
  welcomeCanvas: document.getElementById('welcome-canvas'),
  messagesThread: document.getElementById('messages-thread'),
  composerInput: document.getElementById('composer-input'),
  btnSend: document.getElementById('btn-send'),
  btnAttach: document.getElementById('btn-attach'),
  btnImageAttach: document.getElementById('btn-image-attach'),

  // Artifact Viewer Elements
  artifactPane: document.getElementById('artifact-pane'),
  artifactTitle: document.getElementById('artifact-title'),
  artifactBadge: document.getElementById('artifact-badge'),
  artifactHeaderIcon: document.getElementById('artifact-header-icon'),
  btnArtifactPreviewTab: document.getElementById('btn-artifact-preview-tab'),
  btnArtifactCodeTab: document.getElementById('btn-artifact-code-tab'),
  btnCopyArtifact: document.getElementById('btn-copy-artifact'),
  btnDownloadArtifact: document.getElementById('btn-download-artifact'),
  btnCloseArtifact: document.getElementById('btn-close-artifact'),
  artifactBrowserMockup: document.getElementById('artifact-browser-mockup'),
  artifactSandboxIframe: document.getElementById('artifact-sandbox-iframe'),
  artifactMarkdownView: document.getElementById('artifact-markdown-view'),
  artifactCodeView: document.getElementById('artifact-code-view'),
  artifactCodeContent: document.getElementById('artifact-code-content'),
  artifactBlockedView: document.getElementById('artifact-blocked-view'),
  artifactLoadingOverlay: document.getElementById('artifact-loading-overlay'),
  artifactLoadingSubtext: document.getElementById('artifact-loading-subtext'),
  artifactStatusFormat: document.getElementById('artifact-status-format'),
  artifactStatusReady: document.getElementById('artifact-status-ready'),
  btnBlockedViewCode: document.getElementById('btn-blocked-view-code'),
  btnBlockedDownload: document.getElementById('btn-blocked-download'),

  // Knowledge Base View Elements
  knowledgeBaseView: document.getElementById('knowledge-base-view'),
  kbReadyState: document.getElementById('kb-ready-state'),
  kbSyncingState: document.getElementById('kb-syncing-state'),
  kbUninitializedState: document.getElementById('kb-uninitialized-state'),
  btnTriggerKbSync: document.getElementById('btn-trigger-kb-sync'),
  btnTriggerKbSyncTop: document.getElementById('btn-trigger-kb-sync-top'),
  btnTestUninitKb: document.getElementById('btn-test-uninit-kb'),
  btnCancelSync: document.getElementById('btn-cancel-sync'),
  btnInitializeKb: document.getElementById('btn-initialize-kb'),
  kbSyncBarFill: document.getElementById('kb-sync-bar-fill'),
  kbStatEpisodes: document.getElementById('kb-stat-episodes'),
  kbStatSyncTime: document.getElementById('kb-stat-sync-time'),
  kbSearchInput: document.getElementById('kb-search-input'),
  kbTranscriptsGrid: document.getElementById('kb-transcripts-grid'),

  // Modals & Dialogs
  modalSourceDetail: document.getElementById('modal-source-detail'),
  modalSourceGuest: document.getElementById('modal-source-guest'),
  modalSourceExcerpt: document.getElementById('modal-source-excerpt'),
  modalSourceEpisode: document.getElementById('modal-source-episode'),
  modalSourceTimestamp: document.getElementById('modal-source-timestamp'),
  modalSourceTopics: document.getElementById('modal-source-topics'),
  modalSourceLink: document.getElementById('modal-source-link'),
  modalSettings: document.getElementById('modal-settings'),
  modalModelError: document.getElementById('modal-model-error'),
  settingsProviderSelect: document.getElementById('settings-provider-select'),
  settingsOllamaUrl: document.getElementById('settings-ollama-url'),
  settingsFastapiUrl: document.getElementById('settings-fastapi-url'),
  settingsToggleOffline: document.getElementById('settings-toggle-offline'),
  btnSaveSettings: document.getElementById('btn-save-settings'),
  btnErrorRetry: document.getElementById('btn-error-retry'),
  btnErrorSwitchCloud: document.getElementById('btn-error-switch-cloud'),

  toastContainer: document.getElementById('toast-container')
};

// ==========================================
// Initialization & Lifecycle
// ==========================================

document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  await updateModelStatusUI();
  await loadConversations();
  renderHistoryList();
  await loadKnowledgeBaseMetadata();
  await loadTranscriptsExplorer();
  await restoreLatestArtifact();
  
  if (state.conversations && state.conversations.length > 0) {
    selectConversation(state.conversations[0].id);
  } else {
    await startNewChat();
  }
});

// ==========================================
// Event Listeners Setup
// ==========================================

function setupEventListeners() {
  // Mobile menu & drawer
  elements.btnMobileMenu.addEventListener('click', toggleMobileSidebar);
  elements.drawerBackdrop.addEventListener('click', closeMobileSidebar);

  // Desktop sidebar toggle
  if (elements.btnDesktopToggleSidebar) {
    elements.btnDesktopToggleSidebar.addEventListener('click', toggleDesktopSidebar);
  }

  // New Chat
  elements.btnNewChat.addEventListener('click', () => {
    startNewChat();
    closeMobileSidebar();
  });

  // Top tabs: Model switching
  elements.tabModelOllama.addEventListener('click', () => switchModelProvider('ollama'));
  elements.tabModelCloud.addEventListener('click', () => switchModelProvider('cloud'));
  elements.providerStatusBadge.addEventListener('click', () => {
    openModal(elements.modalSettings);
  });

  // Navigation Links
  elements.navKnowledgeBase.addEventListener('click', () => {
    switchMainView('knowledge-base');
    closeMobileSidebar();
  });

  if (elements.btnSidebarAddKb) {
    elements.btnSidebarAddKb.addEventListener('click', () => {
      openModal(elements.modalAddKb);
      closeMobileSidebar();
    });
  }

  elements.navOpenArtifact.addEventListener('click', () => {
    if (state.currentArtifact) {
      openArtifact(state.currentArtifact);
      switchMainView('chat');
    } else {
      showToast('No active artifact generated yet. Ask for a card or report in chat!');
    }
    closeMobileSidebar();
  });

  elements.navSettings.addEventListener('click', () => {
    openModal(elements.modalSettings);
    closeMobileSidebar();
  });

  // Composer events
  elements.composerInput.addEventListener('input', handleComposerInput);
  elements.composerInput.addEventListener('keydown', handleComposerKeyDown);
  elements.btnSend.addEventListener('click', sendMessage);

  // Suggested Prompts click delegation
  elements.welcomeCanvas.addEventListener('click', (e) => {
    const card = e.target.closest('.prompt-card');
    if (card && card.dataset.prompt) {
      elements.composerInput.value = card.dataset.prompt;
      handleComposerInput();
      sendMessage();
    }
  });

  // Attachments button
  elements.btnAttach.addEventListener('click', () => {
    showToast('Prompt library & attachments loaded');
  });

  elements.btnImageAttach.addEventListener('click', () => {
    showToast('Image OCR & Multimodal reference ready');
  });

  // Artifact Controls
  elements.btnToggleArtifact.addEventListener('click', () => {
    if (state.isArtifactOpen) {
      closeArtifact();
    } else if (state.currentArtifact) {
      openArtifact(state.currentArtifact);
    } else {
      showToast('No artifact active. Prompt the assistant to build one!');
    }
  });

  elements.btnCloseArtifact.addEventListener('click', closeArtifact);
  elements.btnArtifactPreviewTab.addEventListener('click', () => switchArtifactTab('preview'));
  elements.btnArtifactCodeTab.addEventListener('click', () => switchArtifactTab('code'));
  elements.btnCopyArtifact.addEventListener('click', copyArtifactCode);
  elements.btnDownloadArtifact.addEventListener('click', downloadArtifact);
  elements.btnBlockedViewCode.addEventListener('click', () => switchArtifactTab('code'));
  elements.btnBlockedDownload.addEventListener('click', downloadArtifact);

  // Knowledge Base Actions
  elements.btnTriggerKbSync.addEventListener('click', startKnowledgeBaseSync);
  if (elements.btnTriggerKbSyncTop) {
    elements.btnTriggerKbSyncTop.addEventListener('click', startKnowledgeBaseSync);
  }
  elements.btnCancelSync.addEventListener('click', cancelKnowledgeBaseSync);
  elements.btnTestUninitKb.addEventListener('click', toggleUninitializedKbView);
  elements.btnInitializeKb.addEventListener('click', () => {
    elements.kbUninitializedState.style.display = 'none';
    elements.kbReadyState.style.display = 'block';
    startKnowledgeBaseSync();
  });

  // Transcripts search
  if (elements.kbSearchInput) {
    elements.kbSearchInput.addEventListener('input', (e) => {
      loadTranscriptsExplorer(e.target.value);
    });
  }

  // Modals close buttons
  document.querySelectorAll('.modal-close-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      closeAllModals();
    });
  });

  // Settings form
  elements.btnSaveSettings.addEventListener('click', saveSettings);
  elements.btnErrorRetry.addEventListener('click', () => {
    closeAllModals();
    updateModelStatusUI();
    showToast('Checking connection to Ollama...');
  });
  elements.btnErrorSwitchCloud.addEventListener('click', () => {
    closeAllModals();
    switchModelProvider('cloud');
  });

  // Topbar More menu
  elements.btnMoreOptions.addEventListener('click', () => {
    openModal(elements.modalSettings);
  });
}

// ==========================================
// View & Navigation Handlers
// ==========================================

function switchMainView(viewName) {
  state.activeView = viewName;
  
  if (viewName === 'chat') {
    elements.knowledgeBaseView.classList.remove('active');
    elements.chatPane.style.display = 'flex';
    elements.topbarViewTitle.textContent = 'Lenny Assistant';
    elements.navKnowledgeBase.classList.remove('active');
    if (state.activeConversationId) {
      document.querySelectorAll('.nav-item.conv-item').forEach(el => {
        if (el.dataset.id === state.activeConversationId) el.classList.add('active');
      });
    }
  } else if (viewName === 'knowledge-base') {
    elements.chatPane.style.display = 'none';
    elements.knowledgeBaseView.classList.add('active');
    elements.topbarViewTitle.textContent = 'Knowledge Base';
    elements.navKnowledgeBase.classList.add('active');
    // Remove active state from conversation items
    document.querySelectorAll('.nav-item.conv-item').forEach(el => el.classList.remove('active'));
    loadKnowledgeBaseSources();
    loadTranscriptsExplorer();
  }
}

function toggleMobileSidebar() {
  elements.sidebar.classList.toggle('open');
  elements.drawerBackdrop.classList.toggle('open');
}

function toggleDesktopSidebar() {
  elements.sidebar.classList.toggle('collapsed');
}

function closeMobileSidebar() {
  elements.sidebar.classList.remove('open');
  elements.drawerBackdrop.classList.remove('open');
}

// ==========================================
// Model Switching & Provider Status
// ==========================================

async function switchModelProvider(provider) {
  state.activeProvider = provider;
  syncProviderTabs(provider);
  const status = await api.setProvider(provider);
  await updateModelStatusUI();

  if (provider === 'ollama' && !status.ollamaAvailable && !api.isOllamaAvailable) {
    openModal(elements.modalModelError);
  }
}

function syncProviderTabs(provider) {
  const isOllama = provider === 'ollama';
  elements.tabModelOllama.classList.toggle('active', isOllama);
  elements.tabModelCloud.classList.toggle('active', !isOllama);
}

async function updateModelStatusUI() {
  const status = await api.getModelStatus();
  state.activeProvider = status.provider;
  syncProviderTabs(status.provider);
  elements.settingsProviderSelect.value = status.provider === 'ollama' ? 'ollama' : 'cloud';

  if (state.activeProvider === 'ollama') {
    if (api.isOllamaAvailable) {
      elements.providerStatusDot.className = 'status-dot ready pulse';
      elements.providerStatusText.textContent = 'Ollama Ready';
      elements.providerStatusBadge.title = 'Ollama is online and ready.';
    } else {
      elements.providerStatusDot.className = 'status-dot unavailable';
      elements.providerStatusText.textContent = 'Offline';
      elements.providerStatusBadge.title = 'Ollama Local server is unreachable.';
    }
  } else {
    elements.providerStatusDot.className = 'status-dot ready pulse';
    elements.providerStatusText.textContent = 'Cloud Active';
    elements.providerStatusBadge.title = 'Cloud provider connection is active.';
  }
}

// ==========================================
// Conversations Management & History
// ==========================================

async function loadConversations() {
  state.conversations = await api.getConversations();
}

async function restoreLatestArtifact() {
  const artifacts = await api.getArtifacts();
  const latest = artifacts[0];
  if (!latest) return;
  state.currentArtifact = {
    id: latest.id,
    title: latest.title,
    type: latest.artifact_type,
    badge: latest.artifact_type === 'html' ? 'Saved Artifact' : 'Markdown Artifact',
    code: cleanArtifactContent(latest.content),
    filename: `${latest.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'artifact'}.${latest.artifact_type === 'html' ? 'html' : 'md'}`
  };
  elements.sidebarArtifactStatus.textContent = 'Saved';
}

function renderHistoryList() {
  elements.historyToday.innerHTML = '';
  elements.historyYesterday.innerHTML = '';
  elements.historyPrevious.innerHTML = '';

  state.conversations.forEach(conv => {
    const item = document.createElement('button');
    item.className = `nav-item conv-item ${conv.id === state.activeConversationId && state.activeView === 'chat' ? 'active' : ''}`;
    item.dataset.id = conv.id;
    item.innerHTML = `
      <span class="material-symbols-outlined">chat_bubble</span>
      <span class="truncate">${escapeHtml(conv.title)}</span>
    `;

    item.addEventListener('click', () => {
      selectConversation(conv.id);
      closeMobileSidebar();
    });

    if (conv.timeGroup === 'Today') {
      elements.historyToday.appendChild(item);
    } else if (conv.timeGroup === 'Yesterday') {
      elements.historyYesterday.appendChild(item);
    } else {
      elements.historyPrevious.appendChild(item);
    }
  });
}

async function selectConversation(convId) {
  state.activeConversationId = convId;
  switchMainView('chat');
  renderHistoryList();

  const conv = await api.getConversation(convId);
  if (!conv || !conv.messages || conv.messages.length === 0) {
    elements.welcomeCanvas.style.display = 'flex';
    elements.messagesThread.style.display = 'none';
    elements.messagesThread.innerHTML = '';
    return;
  }

  elements.welcomeCanvas.style.display = 'none';
  elements.messagesThread.style.display = 'flex';
  elements.messagesThread.innerHTML = '';

  conv.messages.forEach(msg => {
    appendMessageToDOM(msg);
  });

  scrollToBottom();
}

async function startNewChat() {
  const newConv = await api.createConversation('New Chat');
  state.activeConversationId = newConv.id;
  await loadConversations();
  renderHistoryList();
  
  elements.welcomeCanvas.style.display = 'flex';
  elements.messagesThread.style.display = 'none';
  elements.messagesThread.innerHTML = '';
  switchMainView('chat');
  elements.composerInput.focus();
}

// ==========================================
// Chat Interaction & Streaming
// ==========================================

function handleComposerInput() {
  const input = elements.composerInput;
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 160) + 'px';
  elements.btnSend.disabled = input.value.trim().length === 0 || state.isStreaming;
}

function handleComposerKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!elements.btnSend.disabled) {
      sendMessage();
    }
  }
}

async function sendMessage() {
  const text = elements.composerInput.value.trim();
  if (!text || state.isStreaming) return;

  // Check Ollama offline state
  if (state.activeProvider === 'ollama' && !api.isOllamaAvailable) {
    openModal(elements.modalModelError);
    return;
  }

  // Clear composer
  elements.composerInput.value = '';
  elements.composerInput.style.height = 'auto';
  elements.btnSend.disabled = true;

  // Hide welcome canvas, show messages thread
  elements.welcomeCanvas.style.display = 'none';
  elements.messagesThread.style.display = 'flex';

  // 1. Append User Message
  const userMsg = {
    id: 'msg-' + Date.now(),
    role: 'user',
    content: text,
    timestamp: formatTime(new Date())
  };
  appendMessageToDOM(userMsg);
  scrollToBottom();

  // Find or create conversation
  let activeConv = state.conversations.find(c => c.id === state.activeConversationId);
  if (activeConv) {
    activeConv.messages.push(userMsg);
    if (activeConv.messages.length === 1) {
      activeConv.title = text.slice(0, 32) + (text.length > 32 ? '...' : '');
      renderHistoryList();
    }
  }

  // 2. Prepare Assistant Message Placeholder with typing indicator
  state.isStreaming = true;
  const assistantMsgId = 'msg-' + (Date.now() + 1);
  const assistantRow = document.createElement('div');
  assistantRow.className = 'message-row assistant';
  assistantRow.id = assistantRowId(assistantMsgId);
  assistantRow.innerHTML = `
    <div class="assistant-avatar">L</div>
    <div class="assistant-card">
      <div class="assistant-content">
        <div class="generating-indicator">
          <span class="material-symbols-outlined spinner-icon">progress_activity</span>
          <span>Searching podcast transcripts and synthesizing answer...</span>
        </div>
      </div>
      <div class="assistant-sources-placeholder"></div>
      <div class="assistant-artifact-placeholder"></div>
    </div>
  `;
  elements.messagesThread.appendChild(assistantRow);
  scrollToBottom();

  let accumulatedContent = '';
  const sourcesReceived = [];
  let attachedArtifact = null;

  const contentContainer = assistantRow.querySelector('.assistant-content');
  const sourcesContainer = assistantRow.querySelector('.assistant-sources-placeholder');
  const artifactContainer = assistantRow.querySelector('.assistant-artifact-placeholder');

  let hasEmittedFirstChunk = false;

  await api.sendMessageStream({
    conversationId: state.activeConversationId,
    message: text,
    onChunk: (chunk) => {
      if (!hasEmittedFirstChunk) {
        contentContainer.innerHTML = '';
        hasEmittedFirstChunk = true;
      }
      accumulatedContent += chunk;
      contentContainer.innerHTML = parseMarkdownToHTML(accumulatedContent);
      scrollToBottom();
    },
    onSource: (source) => {
      sourcesReceived.push(source);
      renderAssistantSources(sourcesContainer, sourcesReceived);
      scrollToBottom();
    },
    onArtifact: (artifact) => {
      attachedArtifact = artifact;
      renderInlineArtifactCard(artifactContainer, artifact);
      // Auto open artifact panel
      openArtifact(artifact);
      scrollToBottom();
    },
    onError: (err) => {
      state.isStreaming = false;
      contentContainer.innerHTML = `
        <div style="color: var(--error); display: flex; align-items: center; gap: 8px;">
          <span class="material-symbols-outlined">error</span>
          <span>${escapeHtml(err.message)}</span>
        </div>
      `;
      elements.btnSend.disabled = false;
    },
    onDone: () => {
      state.isStreaming = false;
      elements.btnSend.disabled = false;
      
      const assistantMsg = {
        id: assistantMsgId,
        role: 'assistant',
        content: accumulatedContent,
        sources: sourcesReceived.length > 0 ? sourcesReceived : undefined,
        artifact: attachedArtifact || undefined,
        timestamp: formatTime(new Date())
      };

      if (activeConv) {
        activeConv.messages.push(assistantMsg);
      }
    }
  });
}

function assistantRowId(msgId) {
  return `assistant-row-${msgId}`;
}

function appendMessageToDOM(msg) {
  if (msg.role === 'user') {
    const row = document.createElement('div');
    row.className = 'message-row user';
    row.innerHTML = `
      <div class="message-bubble-user">
        ${escapeHtml(msg.content)}
      </div>
    `;
    elements.messagesThread.appendChild(row);
  } else {
    const row = document.createElement('div');
    row.className = 'message-row assistant';
    row.innerHTML = `
      <div class="assistant-avatar">L</div>
      <div class="assistant-card">
        <div class="assistant-content">
          ${parseMarkdownToHTML(msg.content)}
        </div>
        <div class="assistant-sources-placeholder"></div>
        <div class="assistant-artifact-placeholder"></div>
      </div>
    `;

    const sourcesContainer = row.querySelector('.assistant-sources-placeholder');
    if (msg.sources && msg.sources.length > 0) {
      renderAssistantSources(sourcesContainer, msg.sources);
    }

    const artifactContainer = row.querySelector('.assistant-artifact-placeholder');
    if (msg.artifact) {
      renderInlineArtifactCard(artifactContainer, msg.artifact);
    }

    elements.messagesThread.appendChild(row);
  }
}

function renderAssistantSources(container, sources) {
  if (!sources || sources.length === 0) return;

  container.innerHTML = `
    <div class="sources-section">
      <div class="sources-heading">Grounded Sources & Citations</div>
      <div class="sources-grid">
        ${sources.map(src => `
          <div class="source-card" data-source-id="${src.id}">
            <div>
              <div class="source-badge-title">
                <span class="source-num">${src.number || '01'}</span>
                <span class="source-title">${escapeHtml(src.guest)}</span>
              </div>
              <div class="source-excerpt">"${escapeHtml(src.excerpt)}"</div>
            </div>
            <div class="source-link-action">
              <span>View source</span>
              <span class="material-symbols-outlined" style="font-size: 16px;">arrow_forward</span>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  container.querySelectorAll('.source-card').forEach(card => {
    card.addEventListener('click', () => {
      const srcId = card.dataset.sourceId;
      const sourceObj = (sources || []).find(s => s.id === srcId);
      if (sourceObj) {
        openSourceDetailModal(sourceObj);
      }
    });
  });
}

function renderInlineArtifactCard(container, artifact) {
  container.innerHTML = `
    <div class="inline-artifact-preview">
      <span class="material-symbols-outlined artifact-card-icon">
        ${artifact.type === 'html' ? 'web' : 'description'}
      </span>
      <div class="artifact-card-meta" style="flex: 1;">
        <h4>${escapeHtml(artifact.title)}</h4>
        <p>${escapeHtml(artifact.badge)}</p>
      </div>
      <span class="material-symbols-outlined" style="font-size: 18px; color: var(--primary);">
        open_in_new
      </span>
    </div>
  `;

  container.querySelector('.inline-artifact-preview').addEventListener('click', () => {
    openArtifact(artifact);
  });
}

function scrollToBottom() {
  elements.chatScrollArea.scrollTop = elements.chatScrollArea.scrollHeight;
}

// ==========================================
// Artifact Viewer Panel Management
// ==========================================

function openArtifact(artifact) {
  state.currentArtifact = artifact;
  state.isArtifactOpen = true;

  elements.artifactPane.classList.remove('closed');
  elements.artifactTitle.textContent = artifact.title;
  elements.artifactBadge.textContent = artifact.badge;
  const previewType = artifactPreviewType(artifact);
  elements.artifactHeaderIcon.textContent = previewType === 'html' ? 'web' : 'description';
  elements.artifactStatusFormat.textContent = previewType === 'html' ? 'Format: HTML5 / CSS3' : 'Format: Markdown';

  switchArtifactTab(state.artifactTab);
}

function closeArtifact() {
  state.isArtifactOpen = false;
  elements.artifactPane.classList.add('closed');
}

function switchArtifactTab(tab) {
  state.artifactTab = tab;
  
  if (tab === 'preview') {
    elements.btnArtifactPreviewTab.classList.add('active');
    elements.btnArtifactCodeTab.classList.remove('active');
    elements.artifactCodeView.style.display = 'none';
    elements.artifactBlockedView.style.display = 'none';

    if (artifactPreviewType(state.currentArtifact) === 'html') {
      elements.artifactBrowserMockup.style.display = 'flex';
      elements.artifactMarkdownView.style.display = 'none';
      renderHtmlInSandbox(state.currentArtifact.code);
    } else {
      elements.artifactBrowserMockup.style.display = 'none';
      elements.artifactMarkdownView.style.display = 'block';
      elements.artifactMarkdownView.innerHTML = parseMarkdownToHTML(cleanArtifactContent(state.currentArtifact.code));
    }
  } else {
    // Code View
    elements.btnArtifactCodeTab.classList.add('active');
    elements.btnArtifactPreviewTab.classList.remove('active');
    elements.artifactBrowserMockup.style.display = 'none';
    elements.artifactMarkdownView.style.display = 'none';
    elements.artifactBlockedView.style.display = 'none';
    elements.artifactCodeView.style.display = 'block';
    
    elements.artifactCodeContent.textContent = state.currentArtifact.code;
  }
}

function cleanArtifactContent(content) {
  return String(content || '')
    .replace(/<!--\s*ARTIFACT_TITLE:.*?-->/gis, '')
    .replace(/<!--\s*ARTIFACT_START\s*-->/gi, '')
    .replace(/<!--\s*ARTIFACT_END\s*-->/gi, '')
    .trim();
}

function artifactPreviewType(artifact) {
  const content = cleanArtifactContent(artifact.code);
  return artifact.type === 'html' && /<[a-z][^>]*>/i.test(content) ? 'html' : 'markdown';
}

function renderHtmlInSandbox(htmlCode) {
  const iframe = elements.artifactSandboxIframe;
  // Inject into sandboxed iframe using srcdoc for security
  iframe.srcdoc = cleanArtifactContent(htmlCode);
}

function copyArtifactCode() {
  if (!state.currentArtifact) return;
  navigator.clipboard.writeText(state.currentArtifact.code).then(() => {
    showToast('Artifact code copied to clipboard!');
  }).catch(() => {
    showToast('Failed to copy to clipboard');
  });
}

function downloadArtifact() {
  if (!state.currentArtifact) return;
  const blob = new Blob([state.currentArtifact.code], {
    type: state.currentArtifact.type === 'html' ? 'text/html' : 'text/markdown'
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = state.currentArtifact.filename || 'artifact.txt';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast(`Downloaded ${a.download}`);
}

// ==========================================
// Knowledge Base View Management (Single Unified Store)
// ==========================================

async function loadKnowledgeBaseMetadata() {
  const metadata = await api.getKnowledgeBaseMetadata();
  
  if (elements.kbStatEpisodes) elements.kbStatEpisodes.textContent = metadata.totalEpisodes;
  if (elements.sidebarKbCount) elements.sidebarKbCount.textContent = `${metadata.totalEpisodes} ep`;
  if (elements.kbStatSyncTime) elements.kbStatSyncTime.textContent = metadata.lastSynced || '2 hours ago';
}

async function loadTranscriptsExplorer(query = '') {
  if (!elements.kbTranscriptsGrid) return;
  const transcripts = await api.getTranscripts(query);
  elements.kbTranscriptsGrid.innerHTML = '';

  if (transcripts.length === 0) {
    elements.kbTranscriptsGrid.innerHTML = `
      <div style="grid-column: span 2; padding: 32px; text-align: center; color: var(--on-surface-variant);">
        <span class="material-symbols-outlined" style="font-size: 32px; color: var(--outline);">search_off</span>
        <p style="margin-top: 8px; font-size: 14px;">No transcript references match "${escapeHtml(query)}"</p>
      </div>
    `;
    return;
  }

  transcripts.forEach(item => {
    const card = document.createElement('div');
    card.className = 'transcript-card';
    card.innerHTML = `
      <div>
        <div class="transcript-guest">
          <span class="material-symbols-outlined" style="color: var(--primary); font-size: 18px;">mic</span>
          <span>${escapeHtml(item.guest)}</span>
          <span style="font-size: 11px; font-weight: normal; color: var(--on-surface-variant); margin-left: auto;">${item.timestamp}</span>
        </div>
        <div class="transcript-quote">"${escapeHtml(item.excerpt)}"</div>
      </div>
      <div>
        <div class="transcript-tags">
          ${(item.topics || []).map(t => `<span class="transcript-tag">${escapeHtml(t)}</span>`).join('')}
        </div>
        <div style="margin-top: 12px; display: flex; justify-content: flex-end;">
          <a href="${item.url || '#'}" target="_blank" rel="noreferrer" class="btn-link-action" style="font-size: 12px;">
            <span>Episode Reference</span>
            <span class="material-symbols-outlined" style="font-size: 14px;">open_in_new</span>
          </a>
        </div>
      </div>
    `;
    elements.kbTranscriptsGrid.appendChild(card);
  });
}

function startKnowledgeBaseSync() {
  elements.kbReadyState.style.display = 'none';
  elements.kbUninitializedState.style.display = 'none';
  elements.kbSyncingState.style.display = 'block';
  elements.kbSyncBarFill.style.width = '10%';

  const step1 = document.getElementById('sync-step-1');
  const step2 = document.getElementById('sync-step-2');
  const step3 = document.getElementById('sync-step-3');
  const step4 = document.getElementById('sync-step-4');

  resetSyncStepsUI();

  api.startSync({
    onProgress: (progress) => {
      elements.kbSyncBarFill.style.width = progress + '%';
    },
    onStep: (stepInfo) => {
      if (stepInfo.step === 2) {
        step1.className = 'sync-step-item done';
        step1.innerHTML = `<span class="material-symbols-outlined" style="font-size: 18px; color: var(--success);">check_circle</span><span>1. Scanning podcast feeds & transcript repository</span>`;
        step2.className = 'sync-step-item active';
        step2.innerHTML = `<span class="material-symbols-outlined spinner-icon" style="font-size: 18px;">sync</span><span>2. Downloading & chunking text segments</span>`;
      } else if (stepInfo.step === 3) {
        step2.className = 'sync-step-item done';
        step2.innerHTML = `<span class="material-symbols-outlined" style="font-size: 18px; color: var(--success);">check_circle</span><span>2. Downloading & chunking text segments</span>`;
        step3.className = 'sync-step-item active';
        step3.innerHTML = `<span class="material-symbols-outlined spinner-icon" style="font-size: 18px;">sync</span><span>3. Generating vector embeddings (${stepInfo.files})</span>`;
      } else if (stepInfo.step === 4) {
        step3.className = 'sync-step-item done';
        step3.innerHTML = `<span class="material-symbols-outlined" style="font-size: 18px; color: var(--success);">check_circle</span><span>3. Generating vector embeddings (142 / 142 episodes)</span>`;
        step4.className = 'sync-step-item active';
        step4.innerHTML = `<span class="material-symbols-outlined spinner-icon" style="font-size: 18px;">sync</span><span>4. Rebuilding vector index & citation graph</span>`;
      }
    },
    onDone: (error) => {
      if (error) {
        elements.kbSyncingState.style.display = 'none';
        elements.kbReadyState.style.display = 'block';
        showToast(`Knowledge Base sync failed: ${error.message}`);
        return;
      }
      step4.className = 'sync-step-item done';
      step4.innerHTML = `<span class="material-symbols-outlined" style="font-size: 18px; color: var(--success);">check_circle</span><span>4. Rebuilding vector index & citation graph</span>`;
      
      setTimeout(async () => {
        elements.kbSyncingState.style.display = 'none';
        elements.kbReadyState.style.display = 'block';
        await loadKnowledgeBaseMetadata();
        showToast('Knowledge Base manually synchronized successfully!');
      }, 500);
    }
  });
}

function cancelKnowledgeBaseSync() {
  api.cancelSync();
  elements.kbSyncingState.style.display = 'none';
  elements.kbReadyState.style.display = 'block';
  showToast('Knowledge base synchronization cancelled.');
}

function resetSyncStepsUI() {
  const step1 = document.getElementById('sync-step-1');
  const step2 = document.getElementById('sync-step-2');
  const step3 = document.getElementById('sync-step-3');
  const step4 = document.getElementById('sync-step-4');

  step1.className = 'sync-step-item active';
  step1.innerHTML = `<span class="material-symbols-outlined spinner-icon" style="font-size: 18px;">sync</span><span>1. Checking for remote changes</span>`;
  step2.className = 'sync-step-item';
  step2.innerHTML = `<span class="material-symbols-outlined" style="font-size: 18px;">radio_button_unchecked</span><span>2. Downloading new episode transcripts</span>`;
  step3.className = 'sync-step-item';
  step3.innerHTML = `<span class="material-symbols-outlined" style="font-size: 18px;">radio_button_unchecked</span><span>3. Processing embeddings & chunks</span>`;
  step4.className = 'sync-step-item';
  step4.innerHTML = `<span class="material-symbols-outlined" style="font-size: 18px;">radio_button_unchecked</span><span>4. Updating vector search index</span>`;
}

function toggleUninitializedKbView() {
  if (elements.kbReadyState.style.display !== 'none') {
    elements.kbReadyState.style.display = 'none';
    elements.kbUninitializedState.style.display = 'block';
  } else {
    elements.kbUninitializedState.style.display = 'none';
    elements.kbReadyState.style.display = 'block';
  }
}

// ==========================================
// Modals & Source Details
// ==========================================

function openSourceDetailModal(source) {
  elements.modalSourceGuest.textContent = source.guest;
  elements.modalSourceExcerpt.textContent = `"${source.excerpt}"`;
  elements.modalSourceEpisode.textContent = source.episode;
  elements.modalSourceTimestamp.textContent = `Timestamp: ${source.timestamp}`;
  elements.modalSourceLink.href = source.url || '#';

  elements.modalSourceTopics.innerHTML = (source.topics || ['Product Management', 'Growth']).map(topic => `
    <span class="artifact-badge" style="background-color: var(--secondary-container); color: var(--on-secondary-container);">${escapeHtml(topic)}</span>
  `).join('');

  openModal(elements.modalSourceDetail);
}

function openModal(modalEl) {
  closeAllModals();
  modalEl.classList.add('open');
}

function closeAllModals() {
  document.querySelectorAll('.modal-backdrop').forEach(modal => {
    modal.classList.remove('open');
  });
}

function saveSettings() {
  const chosenProvider = elements.settingsProviderSelect.value;
  const isOfflineSimulated = elements.settingsToggleOffline.checked;

  API_CONFIG.ollamaBaseUrl = elements.settingsOllamaUrl.value;
  API_CONFIG.fastApiBaseUrl = elements.settingsFastapiUrl.value;

  api.toggleOllamaAvailability(!isOfflineSimulated);
  switchModelProvider(chosenProvider);

  closeAllModals();
  showToast('Settings saved successfully!');
}

// ==========================================
// Toast Notification System
// ==========================================

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `
    <span class="material-symbols-outlined" style="font-size: 18px; color: var(--on-primary-container);">info</span>
    <span>${escapeHtml(message)}</span>
  `;
  elements.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, 3200);
}

// ==========================================
// Formatting Helpers & Lightweight Markdown
// ==========================================

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatTime(date) {
  let hours = date.getHours();
  let minutes = date.getMinutes();
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12;
  hours = hours ? hours : 12;
  minutes = minutes < 10 ? '0' + minutes : minutes;
  return `${hours}:${minutes} ${ampm}`;
}

function parseMarkdownToHTML(markdown) {
  if (!markdown) return '';

  let html = markdown;

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Bold & Italic
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');

  // Blockquotes
  html = html.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');

  // Horizontal rules
  html = html.replace(/^---$/gim, '<hr>');

  // Markdown Tables
  const lines = html.split('\n');
  let inTable = false;
  let tableHtml = '';
  const newLines = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith('|') && line.endsWith('|')) {
      if (line.includes('---')) continue; // skip separator row
      if (!inTable) {
        inTable = true;
        tableHtml = '<table>';
      }
      const cells = line.split('|').slice(1, -1);
      const isHeader = !tableHtml.includes('<tbody>');
      tableHtml += '<tr>';
      cells.forEach(c => {
        const tag = isHeader ? 'th' : 'td';
        tableHtml += `<${tag}>${c.trim()}</${tag}>`;
      });
      tableHtml += '</tr>';
    } else {
      if (inTable) {
        inTable = false;
        tableHtml += '</table>';
        newLines.push(tableHtml);
      }
      newLines.push(lines[i]);
    }
  }
  if (inTable) {
    tableHtml += '</table>';
    newLines.push(tableHtml);
  }

  html = newLines.join('\n');

  // Unordered list items
  html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
  html = html.replace(/^- (.*$)/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gims, '<ul>$1</ul>');

  // Numbered list items
  html = html.replace(/^\d+\.\s+(.*$)/gim, '<li>$1</li>');

  // Paragraphs
  const paragraphs = html.split(/\n\n+/);
  html = paragraphs.map(p => {
    p = p.trim();
    if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<table') || p.startsWith('<hr') || p.startsWith('<blockquote')) {
      return p;
    }
    return p ? `<p>${p.replace(/\n/g, '<br>')}</p>` : '';
  }).join('');

  return html;
}
