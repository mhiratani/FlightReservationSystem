# Flight API (FastAPI)

フライト予約管理のREST APIサーバーです。

## 機能

- フライトデータのCRUD操作
- データのエクスポート/インポート
- EチケットPDFのアップロード
- 管理画面の提供

## セットアップ

```bash
pip install -r requirements.txt
```

## 起動

```bash
# 開発モード
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# 本番モード
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

## API ドキュメント

起動後、以下のURLでSwagger UIにアクセスできます：
- http://localhost:8002/docs

## エンドポイント

- `GET /api/flights` - フライト一覧取得
- `GET /api/flights/{id}` - 特定フライト取得
- `POST /api/flights` - フライト作成
- `PUT /api/flights/{id}` - フライト更新
- `DELETE /api/flights/{id}` - フライト削除
- `GET /api/flights/export` - データエクスポート
- `POST /api/flights/import` - データインポート
- `POST /api/flights/{id}/upload-eticket` - Eチケットアップロード
- `GET /admin` - 管理画面
