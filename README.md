# ✈️ フライト予約管理システム

フライトの予約情報と搭乗記録を管理するためのシステムです。

## 🆕 新機能: PDFからの自動インポート

**Claude APIを使用したEチケットPDF解析機能**を実装しました！

### 主な機能
- EチケットPDFをアップロードするだけで、フライト情報を自動抽出
- **1つのPDFに複数の便が含まれている場合も対応**
- 抽出されたデータをプレビューで確認・編集可能
- 個別登録または一括登録が選択可能

### 使い方
1. 管理画面（http://localhost:8002/admin）にアクセス
2. 「📄 PDFからインポート」セクションでPDFファイルを選択
3. 「📥 PDFから情報を抽出」ボタンをクリック
4. 抽出されたデータを確認・必要に応じて編集
5. 「✅ すべて登録」または個別に登録

### セットアップ
環境変数に以下を追加してください：

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## 📋 システム構成

このシステムは以下のコンポーネントで構成されています：

- **PostgreSQL**: フライトデータを保存するデータベース
- **flight-api (FastAPI)**: フライト管理のREST API
- **flight-node-server (Node.js/Express)**: フライト情報をHTML形式で提供するサーバー

## 🗂️ データベーススキーマ

### flightsテーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | SERIAL PRIMARY KEY | 主キー |
| flight_date | DATE | 搭乗日付 |
| departure_airport | VARCHAR(3) | 出発地（3レターコード） |
| arrival_airport | VARCHAR(3) | 到着地（3レターコード） |
| reservation_number | VARCHAR(50) | 予約番号 |
| flight_number | VARCHAR(20) | フライト番号 |
| eticket_pdf_path | VARCHAR(255) | EチケットPDFのパス |
| seat_number | VARCHAR(10) | 座席番号 |
| status | VARCHAR(20) | ステータス（Reserved/Boarded/Cancelled） |
| departure_time | TIME | 出発時刻 |
| arrival_time | TIME | 到着時刻 |
| notes | TEXT | メモ |
| payment_amount | NUMERIC(10, 2) | 支払額 |
| currency | VARCHAR(3) | 通貨コード（デフォルト: JPY） |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |

## 🚀 起動方法

### 1. 環境変数の設定

`.env`ファイルを編集してPostgreSQLのパスワードとAnthropicのAPIキーを設定してください：

```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
FLIGHT_DB=flight_db
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 2. Docker Composeで起動

```bash
cd FlightReservationSystem
docker-compose up -d
```

### 3. サービスの確認

起動後、以下のURLでサービスにアクセスできます：

- **管理画面**: http://localhost:8002/admin
- **API ドキュメント**: http://localhost:8002/docs
- **PostgreSQL**: localhost:55433

## 📡 API エンドポイント

### flight-api (ポート: 8002)

| メソッド | エンドポイント | 説明 |
|---------|--------------|------|
| GET | `/api/flights` | フライト一覧取得 |
| GET | `/api/flights/{id}` | 特定フライト取得 |
| POST | `/api/flights` | フライト追加 |
| PUT | `/api/flights/{id}` | フライト更新 |
| DELETE | `/api/flights/{id}` | フライト削除 |
| GET | `/api/flights/export` | データエクスポート |
| POST | `/api/flights/import` | データインポート |
| POST | `/api/flights/{id}/upload-eticket` | Eチケットアップロード |
| **POST** | **`/api/flights/import-from-pdf`** | **PDFからフライト情報を抽出（新機能）** |
| GET | `/admin` | 管理画面 |

### flight-node-server (ポート: 3005)

| メソッド | エンドポイント | 説明 |
|---------|--------------|------|
| GET | `/api/flights/html` | フライト一覧をHTML形式で取得 |
| GET | `/api/flights` | フライト一覧をJSON形式で取得 |
| GET | `/api/flights/export` | データエクスポート |
| POST | `/api/flights/import` | データインポート |

## 💻 管理画面の使い方

### PDFからのインポート（新機能）

1. http://localhost:8002/admin にアクセス
2. 「📄 PDFからインポート」セクションでEチケットPDFを選択
3. 「📥 PDFから情報を抽出」をクリック
4. 抽出されたフライト情報がプレビューテーブルに表示されます
5. 必要に応じて情報を編集
6. 「✅ すべて登録」で一括登録、または個別に登録

**対応する情報：**
- 搭乗日付
- フライト番号
- 出発空港・到着空港（3レターコード）
- 出発時刻・到着時刻
- 予約番号
- 座席番号
- 支払額・通貨

### 新規フライト追加

1. http://localhost:8002/admin にアクセス
2. 「新規フライト追加」フォームに情報を入力
3. 「追加」ボタンをクリック

### フライト編集

1. フライト一覧から「編集」ボタンをクリック
2. 編集フォームで情報を変更
3. EチケットPDFをアップロード可能
4. 「更新」ボタンをクリック

### データのエクスポート/インポート

- **エクスポート**: 「📥 エクスポート」ボタンでJSON形式でダウンロード
- **インポート**: APIエンドポイントを使用

## 🔧 開発

### ローカルでの開発

```bash
# FastAPI（開発モード）
cd flight-api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002

# Node.js server（開発モード）
cd flight-node-server
npm install
npm run dev
```

### データベース接続

ローカル開発時は以下の接続情報を使用：

```
Host: localhost
Port: 55433
Database: flight_db
User: postgres
Password: (.envに設定したパスワード)
```

## 📁 プロジェクト構造

```
FlightReservationSystem/
├── docker-compose.yml
├── .env
├── .gitignore
├── README.md
├── flight-api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── database.py
│   │   └── static/
│   │       └── admin.html
│   └── pdfs/               # EチケットPDF保存ディレクトリ
└── flight-node-server/
    ├── Dockerfile
    ├── package.json
    └── server.js
```

## 🔒 セキュリティ

- `.env`ファイルは`.gitignore`に含まれており、Gitにコミットされません
- 本番環境では必ず強力なパスワードを使用してください
- **Anthropic APIキーは機密情報です。絶対に公開しないでください**
- EチケットPDFは`flight-api/pdfs/`ディレクトリに保存されます

## 📝 注意事項

- このシステムは独立した環境として設計されており、StellaKanonWebとは完全に分離されています
- ポート番号は以下の通り設定されています：
  - PostgreSQL: 55433 (StellaKanonWebの55432と重複しないように設定)
  - flight-api: 8002
  - flight-node-server: 3005
- PDFインポート機能を使用するには、Anthropic API キーが必要です
- Claude API（claude-haiku-4-5-20251001）を使用しています

## 🛠️ トラブルシューティング

### コンテナが起動しない場合

```bash
# ログを確認
docker-compose logs

# コンテナを再起動
docker-compose down
docker-compose up -d
```

### データベース接続エラー

- `.env`ファイルの設定を確認
- PostgreSQLコンテナが起動しているか確認: `docker-compose ps`

### PDFインポートが動作しない

- `ANTHROPIC_API_KEY`が`.env`に正しく設定されているか確認
- APIキーが有効か確認
- コンテナを再起動: `docker-compose restart flight-api`

### ポート競合エラー

- 既に使用されているポートがないか確認
- `docker-compose.yml`のポート設定を変更

## 📞 サポート

問題が発生した場合は、ログを確認してください：

```bash
docker-compose logs flight-api
docker-compose logs flight-node-server
docker-compose logs postgres-db
