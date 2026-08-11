// ============================================================
// 東証お気に入り銘柄 株価チャート配信システム - JavaScript Logic
// Supabase Auth & DB (最大30件お気に入り登録制限対応)
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  // --- State Variables ---
  let supabaseClient = null;
  let currentUser = null;
  let favoritesList = [];
  let isSignUpMode = false;

  // --- DOM Elements ---
  const configBanner = document.getElementById('config-banner');
  const btnOpenConfigModal = document.getElementById('btn-open-config-modal');
  const btnCloseConfigModal = document.getElementById('btn-close-config-modal');
  const configModal = document.getElementById('config-modal');
  const configForm = document.getElementById('config-form');
  const inputCfgUrl = document.getElementById('cfg-supabase-url');
  const inputCfgKey = document.getElementById('cfg-supabase-key');

  const userStatusBar = document.getElementById('user-status-bar');
  const userEmailDisplay = document.getElementById('user-email-display');
  const btnLogout = document.getElementById('btn-logout');

  const authSection = document.getElementById('auth-section');
  const authTitle = document.getElementById('auth-title');
  const authForm = document.getElementById('auth-form');
  const inputEmail = document.getElementById('input-email');
  const inputPassword = document.getElementById('input-password');
  const authErrorMsg = document.getElementById('auth-error-msg');
  const authBtnText = document.getElementById('auth-btn-text');
  const btnToggleAuth = document.getElementById('btn-toggle-auth');
  const authToggleText = document.getElementById('auth-toggle-text');

  const dashboardSection = document.getElementById('dashboard-section');
  const addStockForm = document.getElementById('add-stock-form');
  const inputTicker = document.getElementById('input-ticker');
  const favoritesCountDisplay = document.getElementById('favorites-count');
  const favoritesLoading = document.getElementById('favorites-loading');
  const emptyState = document.getElementById('empty-state');
  const favoritesListUl = document.getElementById('favorites-list');

  // --- Initialize Supabase ---
  function initSupabase() {
    const config = window.SUPABASE_CONFIG;
    if (!config || !config.url || !config.anonKey || config.url.includes('YOUR_SUPABASE_URL')) {
      configBanner.classList.remove('hidden');
      return false;
    }
    try {
      supabaseClient = window.supabase.createClient(config.url, config.anonKey);
      configBanner.classList.add('hidden');
      setupAuthListener();
      return true;
    } catch (err) {
      console.error('Supabase Client Init Error:', err);
      configBanner.classList.remove('hidden');
      return false;
    }
  }

  // --- Auth State Change Listener ---
  function setupAuthListener() {
    if (!supabaseClient) return;

    supabaseClient.auth.onAuthStateChange((event, session) => {
      if (session && session.user) {
        currentUser = session.user;
        showDashboardView();
        loadUserFavorites();
      } else {
        currentUser = null;
        showAuthView();
      }
    });
  }

  // --- View Switchers ---
  function showAuthView() {
    authSection.classList.remove('hidden');
    dashboardSection.classList.add('hidden');
    userStatusBar.classList.add('hidden');
  }

  function showDashboardView() {
    authSection.classList.add('hidden');
    dashboardSection.classList.remove('hidden');
    userStatusBar.classList.remove('hidden');
    if (currentUser) {
      userEmailDisplay.textContent = currentUser.email;
    }
  }

  // --- Auth Form Actions (Login / Signup) ---
  authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    authErrorMsg.classList.add('hidden');
    authErrorMsg.textContent = '';

    if (!supabaseClient) {
      authErrorMsg.textContent = 'Supabaseの接続設定を完了してください。';
      authErrorMsg.classList.remove('hidden');
      return;
    }

    const email = inputEmail.value.trim();
    const password = inputPassword.value.trim();

    try {
      let result;
      if (isSignUpMode) {
        result = await supabaseClient.auth.signUp({ email, password });
      } else {
        result = await supabaseClient.auth.signInWithPassword({ email, password });
      }

      if (result.error) {
        authErrorMsg.textContent = translateAuthError(result.error.message);
        authErrorMsg.classList.remove('hidden');
      } else if (isSignUpMode && result.data.user && !result.data.session) {
        authErrorMsg.textContent = '登録確認メールを送信しました。メール内のリンクをクリックしてください。';
        authErrorMsg.classList.remove('hidden');
      }
    } catch (err) {
      authErrorMsg.textContent = '認証処理中にエラーが発生しました。';
      authErrorMsg.classList.remove('hidden');
    }
  });

  // Toggle Login <-> Signup
  btnToggleAuth.addEventListener('click', () => {
    isSignUpMode = !isSignUpMode;
    if (isSignUpMode) {
      authTitle.textContent = '新規アカウント登録';
      authBtnText.textContent = '新規登録';
      authToggleText.textContent = 'すでにアカウントをお持ちですか？';
      btnToggleAuth.textContent = 'ログイン';
    } else {
      authTitle.textContent = 'ログイン';
      authBtnText.textContent = 'ログイン';
      authToggleText.textContent = 'アカウントをお持ちでないですか？';
      btnToggleAuth.textContent = '新規登録';
    }
  });

  // Logout
  btnLogout.addEventListener('click', async () => {
    if (supabaseClient) {
      await supabaseClient.auth.signOut();
    }
  });

  // --- Load Favorites ---
  async function loadUserFavorites() {
    if (!supabaseClient || !currentUser) return;

    favoritesLoading.classList.remove('hidden');
    favoritesListUl.innerHTML = '';
    emptyState.classList.add('hidden');

    try {
      const { data, error } = await supabaseClient
        .from('user_favorites')
        .select('*')
        .eq('user_id', currentUser.id)
        .order('created_at', { ascending: true });

      favoritesLoading.classList.add('hidden');

      if (error) {
        console.error('Error fetching favorites:', error);
        return;
      }

      favoritesList = data || [];
      renderFavoritesList();
    } catch (err) {
      favoritesLoading.classList.add('hidden');
      console.error('Fetch error:', err);
    }
  }

  // Render List
  function renderFavoritesList() {
    favoritesCountDisplay.textContent = favoritesList.length;
    favoritesListUl.innerHTML = '';

    if (favoritesList.length === 0) {
      emptyState.classList.remove('hidden');
      return;
    }

    emptyState.classList.add('hidden');

    favoritesList.forEach((item) => {
      const li = document.createElement('li');
      li.className = 'favorite-item';

      const tickerFormatted = item.ticker.endsWith('.T') ? item.ticker : `${item.ticker}.T`;
      const stockName = item.stock_name || `東証 ${item.ticker}`;

      li.innerHTML = `
        <div class="stock-info">
          <span class="stock-badge">${tickerFormatted}</span>
          <span class="stock-name">${escapeHtml(stockName)}</span>
        </div>
        <button class="btn-delete-stock" data-id="${item.id}" data-ticker="${item.ticker}" title="削除">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      `;
      favoritesListUl.appendChild(li);
    });

    // Attach Delete Listeners
    document.querySelectorAll('.btn-delete-stock').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        const ticker = e.currentTarget.getAttribute('data-ticker');
        await deleteFavoriteStock(id, ticker);
      });
    });
  }

  // --- Add Stock ---
  addStockForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const rawTicker = inputTicker.value.trim().toUpperCase();
    const cleanTicker = rawTicker.replace('.T', '');

    if (!/^[0-9]{4}$/.test(cleanTicker)) {
      alert('銘柄コードは半角数字4桁（例: 7203）を入力してください。');
      return;
    }

    if (favoritesList.length >= 30) {
      alert('お気に入り銘柄は最大30件まで登録可能です。既存の銘柄を削除してから追加してください。');
      return;
    }

    // Check duplicate
    if (favoritesList.some(item => item.ticker === cleanTicker || item.ticker === `${cleanTicker}.T`)) {
      alert(`銘柄コード ${cleanTicker} はすでに登録されています。`);
      return;
    }

    try {
      const { data, error } = await supabaseClient
        .from('user_favorites')
        .insert([
          {
            user_id: currentUser.id,
            ticker: cleanTicker,
            stock_name: `東証コード ${cleanTicker}`
          }
        ])
        .select();

      if (error) {
        alert(`登録エラー: ${error.message}`);
      } else {
        inputTicker.value = '';
        await loadUserFavorites();
      }
    } catch (err) {
      alert('登録処理中にエラーが発生しました。');
    }
  });

  // --- Delete Stock ---
  async function deleteFavoriteStock(id, ticker) {
    if (!confirm(`銘柄コード ${ticker} をお気に入りから削除しますか？`)) return;

    try {
      const { error } = await supabaseClient
        .from('user_favorites')
        .delete()
        .eq('id', id);

      if (error) {
        alert(`削除エラー: ${error.message}`);
      } else {
        await loadUserFavorites();
      }
    } catch (err) {
      alert('削除処理中にエラーが発生しました。');
    }
  }

  // --- Modal Config Management ---
  btnOpenConfigModal.addEventListener('click', () => {
    inputCfgUrl.value = window.localStorage.getItem('SUPABASE_URL') || '';
    inputCfgKey.value = window.localStorage.getItem('SUPABASE_ANON_KEY') || '';
    configModal.classList.remove('hidden');
  });

  btnCloseConfigModal.addEventListener('click', () => {
    configModal.classList.add('hidden');
  });

  configForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const url = inputCfgUrl.value.trim();
    const key = inputCfgKey.value.trim();

    window.localStorage.setItem('SUPABASE_URL', url);
    window.localStorage.setItem('SUPABASE_ANON_KEY', key);

    window.SUPABASE_CONFIG = { url, anonKey: key };
    configModal.classList.add('hidden');
    initSupabase();
  });

  // Helpers
  function translateAuthError(msg) {
    if (msg.includes('Invalid login credentials')) return 'メールアドレスまたはパスワードが正しくありません。';
    if (msg.includes('User already registered')) return 'このメールアドレスは既に登録されています。';
    if (msg.includes('Password should be at least')) return 'パスワードは6文字以上で指定してください。';
    return msg;
  }

  function escapeHtml(str) {
    return str.replace(/[&<>"']/g, (m) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
    }[m]));
  }

  // Boot Application
  initSupabase();
});
