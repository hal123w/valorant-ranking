# valorantランキング

Valorant の X（Twitter）クリップを URL 投稿で集め、公式埋め込みで再生し、アプリ内視聴回数でランキングする Web アプリです。

動画の再ホストはしません。権利は各投稿者等に帰属します。

## セットアップ（ローカル）

```bash
cd valorant-ranking
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # または cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

ブラウザで http://127.0.0.1:8000/

## テスト

```bash
python manage.py test
```

## 主な機能

- タブ: 最新 / 24時間 / 1週間 / 歴代（アプリ内視聴回数）
- 詳細を開くと埋め込み再生＆視聴カウント（同一セッション短時間は再カウントしない）
- 投稿はログイン必須（メール＋パスワード）。X の投稿 URL のみ
- 通報（ログイン不要）。削除は Django admin（superuser）
- 利用規約・プライバシー（簡易）

## GitHub リポジトリ作成〜push

ローカルで初回コミット済みの場合:

1. GitHub で空のリポジトリを作成（例: `valorant-ranking`）
2. 以下を実行:

```bash
git remote add origin https://github.com/<your-user>/valorant-ranking.git
git branch -M main
git push -u origin main
```

`gh` がある場合:

```bash
gh repo create valorant-ranking --private --source=. --remote=origin --push
```

## Render デプロイ（概要）

1. GitHub に push
2. Render で Web Service を作成しリポジトリを接続
3. Build Command: `./build.sh`（Linux）※ Windows 改行の場合は Render 上で `bash build.sh`
4. Start Command: `gunicorn config.wsgi:application`
5. 環境変数: `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL`（PostgreSQL）, `ALLOWED_HOSTS`
6. 初回デプロイ後に shell で `createsuperuser`

## 運用メモ

- Valorant かどうかは自動判定しません。投稿時の同意＋目視＋通報で運用してください
- 削除依頼・通報は admin の Report / Clip から確認・削除します
