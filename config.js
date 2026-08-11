// Supabase 初期接続設定ファイル
// ご自身のSupabase URLおよびanonKeyを設定してください。
// WEB画面の設定モーダルから入力・保存することも可能です。

window.SUPABASE_CONFIG = {
  url: window.localStorage.getItem('SUPABASE_URL') || "YOUR_SUPABASE_URL",
  anonKey: window.localStorage.getItem('SUPABASE_ANON_KEY') || "YOUR_SUPABASE_ANON_KEY"
};
