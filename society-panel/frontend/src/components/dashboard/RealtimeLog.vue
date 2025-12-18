<!-- Real-time WebSocket log viewer for simulation events. -->
<template>
  <div class="log-panel panel-container">
    <div class="log-header">
      <h3>Real-time Event Log</h3>
      <div class="header-filters">
        <div class="dropdown" ref="levelDropdownRef">
          <button class="dropdown-btn" @click.stop="toggleLevelDropdown">
            <span class="dropdown-label">Level</span>
            <span class="dropdown-count" v-if="selectedLevels.length < logLevels.length">{{ selectedLevels.length }}</span>
            <span class="dropdown-arrow">▾</span>
          </button>
          <div v-show="showLevelDropdown" class="dropdown-menu">
            <label v-for="level in logLevels" :key="level" class="dropdown-item">
              <input type="checkbox" v-model="selectedLevels" :value="level" />
              <span :class="['item-dot', 'level-' + level.toLowerCase()]"></span>
              <span class="item-text">{{ level }}</span>
            </label>
          </div>
        </div>
        
        <div class="dropdown" ref="categoryDropdownRef">
          <button class="dropdown-btn" @click.stop="toggleCategoryDropdown">
            <span class="dropdown-label">Category</span>
            <span class="dropdown-count" v-if="selectedCategoryCount < categories.length">{{ selectedCategoryCount }}</span>
            <span class="dropdown-arrow">▾</span>
          </button>
          <div v-show="showCategoryDropdown" class="dropdown-menu">
            <label v-for="cat in categories" :key="cat.value" class="dropdown-item">
              <input type="checkbox" v-model="selectedCategories" :value="cat.value" />
              <span :class="['item-dot', 'cat-' + cat.value]"></span>
              <span class="item-text">{{ cat.label }}</span>
            </label>
          </div>
        </div>
      </div>
    </div>

    <div class="log-actions">
      <button @click="toggleConnection" :class="['btn-toggle', connectionStatus]">
        {{ isConnected ? 'Disconnect' : 'Connect' }}
      </button>
      <button @click="clearLogs" :disabled="!logs.length" class="btn-clear">Clear Logs</button>
      
      <div class="search-box">
        <input 
          type="text" 
          v-model="searchQuery" 
          placeholder="Search logs..."
          class="search-input"
        />
        <span v-if="searchQuery" class="clear-search" @click="searchQuery = ''">×</span>
      </div>
    </div>

    <div class="log-window" ref="logWindowRef">
      <div v-for="(log, index) in filteredLogs" :key="index" :class="['log-entry', log.category]">
        <span class="log-time">{{ log.tick }}</span>
        <span :class="['log-level', log.level?.toLowerCase()]">{{ log.level || 'OUT' }}</span>
        <span :class="['log-category', log.category]">{{ getCategoryLabel(log.category) }}</span>
        <span class="log-message" :title="log.payload" v-html="highlightSearch(log.payload)"></span>
      </div>
      <div v-if="!filteredLogs.length" class="log-placeholder">
        <span class="placeholder-icon"><AppIcons name="connection" :size="64" /></span>
        <p v-if="!isConnected">Connect to view real-time events</p>
        <p v-else-if="logs.length">No logs match current filters</p>
        <p v-else>Waiting for log entries...</p>
      </div>
    </div>
    
    <div class="log-stats" v-if="totalReceived">
      <span>Total: {{ totalReceived }}</span>
      <span>Showing: {{ filteredLogs.length }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, onMounted, nextTick } from 'vue';
import AppIcons from '../icons/AppIcons.vue';

const logs = ref([]);
const totalReceived = ref(0);
const isConnected = ref(false);
const connectionStatus = ref('disconnected');
const logWindowRef = ref(null);
let socket = null;

const searchQuery = ref('');
const logLevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'OUTPUT'];
const selectedLevels = ref(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'OUTPUT']);

const categories = [
  { value: 'agent', label: 'Agent' },
  { value: 'action', label: 'Action' },
  { value: 'env', label: 'Env' },
  { value: 'kernel', label: 'Kernel' },
  { value: 'other', label: 'Other' }
];
const selectedCategories = ref(['agent', 'action', 'env', 'kernel', 'other', 'system']);

const selectedCategoryCount = computed(() => {
  return categories.filter(cat => selectedCategories.value.includes(cat.value)).length;
});

const showLevelDropdown = ref(false);
const showCategoryDropdown = ref(false);
const levelDropdownRef = ref(null);
const categoryDropdownRef = ref(null);

const toggleLevelDropdown = () => {
  showLevelDropdown.value = !showLevelDropdown.value;
  showCategoryDropdown.value = false;
};

const toggleCategoryDropdown = () => {
  showCategoryDropdown.value = !showCategoryDropdown.value;
  showLevelDropdown.value = false;
};

const closeAllDropdowns = (event) => {
  if (levelDropdownRef.value && !levelDropdownRef.value.contains(event.target)) {
    showLevelDropdown.value = false;
  }
  if (categoryDropdownRef.value && !categoryDropdownRef.value.contains(event.target)) {
    showCategoryDropdown.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', closeAllDropdowns);
});

const categoryLabels = {
  agent: 'Agent',
  action: 'Action',
  env: 'Env',
  kernel: 'Kernel',
  other: 'Other',
  system: 'System'
};

const getCategoryLabel = (category) => {
  return categoryLabels[category] || category || 'Log';
};

const highlightSearch = (text) => {
  if (!searchQuery.value || !text) return text;
  const query = searchQuery.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${query})`, 'gi');
  return text.replace(regex, '<mark class="highlight">$1</mark>');
};

const filteredLogs = computed(() => {
  return logs.value.filter(log => {
    if (log.name === 'HEARTBEAT') return false;
    if (log.level && !selectedLevels.value.includes(log.level)) return false;
    if (log.category && !selectedCategories.value.includes(log.category)) return false;
    
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase();
      const matchPayload = log.payload?.toLowerCase().includes(query);
      const matchName = log.name?.toLowerCase().includes(query);
      const matchCategory = log.category?.toLowerCase().includes(query);
      if (!matchPayload && !matchName && !matchCategory) return false;
    }
    
    return true;
  });
});

const scrollToTop = () => {
  nextTick(() => {
    if (logWindowRef.value) {
      logWindowRef.value.scrollTop = 0;
    }
  });
};

const connect = () => {
  socket = new WebSocket('ws://localhost:8001/ws');
  connectionStatus.value = 'connecting';

  socket.onopen = () => {
    isConnected.value = true;
    connectionStatus.value = 'connected';
    scrollToTop();
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      logs.value.unshift({
        tick: data.tick,
        name: data.name,
        payload: data.payload,
        category: data.category,
        level: data.level
      });
      totalReceived.value++;
      if (logs.value.length > 500) logs.value.pop();
      scrollToTop();
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  };

  socket.onclose = () => {
    isConnected.value = false;
    connectionStatus.value = 'disconnected';
    logs.value.unshift({ 
      tick: 'SYS', 
      name: 'System', 
      payload: 'Disconnected from log stream.', 
      category: 'system',
      level: 'INFO'
    });
    scrollToTop();
    socket = null;
  };

  socket.onerror = (error) => {
    console.error('WebSocket Error:', error);
    isConnected.value = false;
    connectionStatus.value = 'error';
    logs.value.unshift({ 
      tick: 'SYS', 
      name: 'System', 
      payload: 'Connection error. Check if backend is running.', 
      category: 'system',
      level: 'ERROR'
    });
    scrollToTop();
  };
};

const disconnect = () => {
  if (socket) socket.close();
};

const toggleConnection = () => {
  if (isConnected.value) disconnect();
  else connect();
};

const clearLogs = () => {
  logs.value = [];
  totalReceived.value = 0;
};

onUnmounted(() => {
  document.removeEventListener('click', closeAllDropdowns);
  disconnect();
});
</script>

<style scoped>
.log-panel {
  display: flex;
  flex-direction: column;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.log-header h3 {
  margin: 0;
}

.header-filters {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.dropdown {
  position: relative;
}

.dropdown-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.625rem;
  border: 0.0625rem solid var(--border-soft);
  border-radius: var(--border-radius-md);
  background-color: var(--surface);
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.dropdown-btn:hover {
  border-color: var(--accent);
  color: var(--text-primary);
}

.dropdown-label {
  font-weight: 500;
}

.dropdown-count {
  background-color: var(--accent);
  color: white;
  font-size: 0.65rem;
  padding: 0.0625rem 0.3125rem;
  border-radius: 0.5rem;
  font-weight: 600;
}

.dropdown-arrow {
  font-size: 0.7rem;
  opacity: 0.6;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 0.25rem);
  right: 0;
  min-width: 8.75rem;
  background-color: var(--surface);
  border: 0.0625rem solid var(--border-soft);
  border-radius: var(--border-radius-md);
  box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.12);
  z-index: 100;
  padding: 0.375rem 0;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem 0.875rem;
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--text-secondary);
  transition: background-color 0.15s;
}

.dropdown-item:hover {
  background-color: var(--bg-inset-soft);
}

.dropdown-item input {
  cursor: pointer;
  accent-color: var(--accent);
  margin: 0;
  width: 0.875rem;
  height: 0.875rem;
  flex-shrink: 0;
}

.item-dot {
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 50%;
  flex-shrink: 0;
}

.item-text {
  flex: 1;
  text-align: left;
}

.item-dot.level-debug { background-color: #6c757d; }
.item-dot.level-info { background-color: #0d6efd; }
.item-dot.level-warning { background-color: #ffc107; }
.item-dot.level-error { background-color: #dc3545; }
.item-dot.level-output { background-color: #198754; }

.item-dot.cat-agent { background-color: #58a6ff; }
.item-dot.cat-action { background-color: #ffc107; }
.item-dot.cat-env { background-color: #3fb950; }
.item-dot.cat-kernel { background-color: #a371f7; }
.item-dot.cat-other { background-color: #6c757d; }

.log-actions {
  display: flex;
  gap: 0.625rem;
  margin-bottom: 0.75rem;
  flex-shrink: 0;
  align-items: center;
}

.log-actions button {
  padding: 0.375rem 0.875rem;
  border-radius: var(--border-radius-md);
  font-size: 0.85rem;
  font-weight: 500;
  border: 0.0625rem solid var(--border-soft);
  background-color: var(--surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
}

.log-actions button:hover {
  border-color: var(--accent);
  color: var(--text-primary);
}

.btn-toggle.connected {
  border-color: var(--accent-strong);
  color: var(--accent-strong);
}

[data-theme="dark"] .btn-toggle.connected {
  border-color: #f85149;
  color: #f85149;
}

.btn-toggle.disconnected {
  border-color: var(--accent);
  color: var(--accent);
}

.btn-toggle.connecting {
  border-color: #d4a017;
  color: #d4a017;
}

.search-box {
  position: relative;
  flex: 1;
  max-width: 18.75rem;
  margin-left: auto;
}

.search-input {
  width: 100%;
  padding: 0.4375rem 1.875rem 0.4375rem 0.75rem;
  border: 0.0625rem solid var(--border-soft);
  border-radius: var(--border-radius-md);
  background-color: var(--surface);
  color: var(--text-primary);
  font-size: 0.85rem;
  outline: none;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: var(--accent);
}

.search-input::placeholder {
  color: var(--text-muted);
}

.clear-search {
  position: absolute;
  right: 0.625rem;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  color: var(--text-muted);
  font-size: 1.1rem;
  line-height: 1;
}

.clear-search:hover {
  color: var(--text-primary);
}

.log-window {
  background-color: var(--bg-inset-soft);
  color: var(--text-muted);
  padding: 0.75rem;
  border-radius: var(--border-radius-md);
  border: 0.0625rem solid var(--border-soft);
  font-family: var(--font-family-mono);
  font-size: 0.8rem;
  flex-grow: 1;
  overflow-y: auto;
  min-height: 0;
}

.log-entry {
  margin-bottom: 0.25rem;
  padding: 0.375rem 0.5rem;
  line-height: 1.5;
  display: grid;
  grid-template-columns: 4.0625rem 3.4375rem 3.125rem 1fr;
  gap: 0.5rem;
  align-items: start;
  border-radius: 0.25rem;
  border-left: 0.1875rem solid transparent;
}

.log-entry:hover {
  background-color: var(--surface);
}

.log-entry.agent { border-left-color: #58a6ff; }
.log-entry.action { border-left-color: #ffc107; }
.log-entry.env { border-left-color: #3fb950; }
.log-entry.kernel { border-left-color: #a371f7; }
.log-entry.other { border-left-color: #6c757d; }
.log-entry.system { border-left-color: #d4a017; }

.log-time {
  color: var(--text-muted);
  font-size: 0.75rem;
  white-space: nowrap;
}

.log-level {
  padding: 0.125rem 0.375rem;
  border-radius: 0.1875rem;
  font-size: 0.65rem;
  font-weight: 700;
  text-align: center;
  white-space: nowrap;
  text-transform: uppercase;
}

.log-level.debug { background-color: #6c757d; color: white; }
.log-level.info { background-color: #0d6efd; color: white; }
.log-level.warning { background-color: #ffc107; color: #212529; }
.log-level.error { background-color: #dc3545; color: white; }
.log-level.output { background-color: #198754; color: white; }

.log-category {
  padding: 0.125rem 0.375rem;
  border-radius: 0.1875rem;
  font-size: 0.7rem;
  font-weight: 600;
  text-align: center;
  white-space: nowrap;
}

.log-category.agent { background-color: rgba(88, 166, 255, 0.2); color: #58a6ff; }
.log-category.action { background-color: rgba(255, 193, 7, 0.2); color: #d4a017; }
.log-category.env { background-color: rgba(46, 160, 67, 0.2); color: #3fb950; }
.log-category.kernel { background-color: rgba(163, 113, 247, 0.2); color: #a371f7; }
.log-category.other { background-color: rgba(108, 117, 125, 0.2); color: #6c757d; }
.log-category.system { background-color: rgba(212, 160, 23, 0.2); color: #d4a017; }

.log-message {
  color: var(--text-primary);
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 8;
  line-clamp: 8;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: default;
  padding-left: 0.75rem;
}

.log-message:hover {
  -webkit-line-clamp: unset;
  line-clamp: unset;
  overflow: visible;
}

.log-message :deep(.highlight) {
  background-color: #ffc107;
  color: #212529;
  padding: 0 0.125rem;
  border-radius: 0.125rem;
}

.log-stats {
  display: flex;
  gap: 1rem;
  padding: 0.5rem 0 0;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.log-placeholder {
  color: var(--text-muted);
  text-align: center;
  padding-top: 15%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.placeholder-icon {
  font-size: 3rem;
  opacity: 0.5;
}

[data-theme="dark"] .log-category.agent { color: #79c0ff; }
[data-theme="dark"] .log-category.env { color: #56d364; }
[data-theme="dark"] .log-category.kernel { color: #bc8cff; }
[data-theme="dark"] .dropdown-menu {
  background-color: var(--bg-inset);
  box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.25);
}
</style>
