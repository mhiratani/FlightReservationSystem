# Flight Node Server (Express)

フライト情報をPostgreSQLから取得してHTML形式で返すNode.jsサーバーです。

## 機能

- フライト一覧をHTML形式で取得
- フライト一覧をJSON形式で取得
- データのエクスポート/インポート

## セットアップ

```bash
npm install
```

## 起動

```bash
# 開発モード（自動リロード）
npm run dev

# 本番モード
npm start
```

## エンドポイント

- `GET /api/flights/html` - フライト一覧をHTML形式で取得
- `GET /api/flights` - フライト一覧をJSON形式で取得
- `GET /api/flights/export` - データをJSONでエクスポート
- `POST /api/flights/import` - JSONデータをインポート
- `GET /health` - ヘルスチェック

## 環境変数

- `PORT` - サーバーポート（デフォルト: 3005）
- `POSTGRES_USER` - PostgreSQLユーザー名
- `POSTGRES_PASSWORD` - PostgreSQLパスワード
- `POSTGRES_HOST` - PostgreSQLホスト
- `POSTGRES_PORT` - PostgreSQLポート
- `FLIGHT_DB` - データベース名
