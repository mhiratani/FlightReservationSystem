FROM node:18-slim

WORKDIR /app

# package.jsonとpackage-lock.jsonをコピー
COPY package*.json ./

# 依存関係のインストール
RUN npm install

# アプリケーションコードをコピー
COPY . .

# ポート公開
EXPOSE 3005

# アプリケーション起動
CMD ["npm", "start"]
