-- ============================================================
-- 東証お気に入り銘柄 株価チャート配信システム - スキーマ定義
-- Supabase SQL Editor に貼り付けて実行してください
-- ============================================================

-- 1. お気に入り銘柄テーブルの作成
CREATE TABLE IF NOT EXISTS public.user_favorites (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    ticker VARCHAR(10) NOT NULL, -- 例: 7203
    stock_name VARCHAR(100),    -- 例: 東証コード 7203
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(user_id, ticker)
);

-- 2. 1ユーザーあたり最大30銘柄の登録制御トリガー関数
CREATE OR REPLACE FUNCTION check_user_favorites_limit()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT COUNT(*) FROM public.user_favorites WHERE user_id = NEW.user_id) >= 30 THEN
        RAISE EXCEPTION 'お気に入り銘柄は最大30件まで登録可能です。';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS enforce_favorites_limit ON public.user_favorites;
CREATE TRIGGER enforce_favorites_limit
    BEFORE INSERT ON public.user_favorites
    FOR EACH ROW
    EXECUTE FUNCTION check_user_favorites_limit();

-- 3. Row Level Security (RLS) 設定
ALTER TABLE public.user_favorites ENABLE ROW LEVEL SECURITY;

-- 自身のデータのみ閲覧可能
CREATE POLICY "Users can view their own favorites"
    ON public.user_favorites FOR SELECT
    USING (auth.uid() = user_id);

-- 自身のデータのみ追加可能
CREATE POLICY "Users can insert their own favorites"
    ON public.user_favorites FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- 自身のデータのみ削除可能
CREATE POLICY "Users can delete their own favorites"
    ON public.user_favorites FOR DELETE
    USING (auth.uid() = user_id);
