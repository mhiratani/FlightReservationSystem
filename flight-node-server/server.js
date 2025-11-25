const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3005;

// PostgreSQL接続設定
const POSTGRES_USER = process.env.POSTGRES_USER || 'postgres';
const POSTGRES_PASSWORD = process.env.POSTGRES_PASSWORD || '';
const POSTGRES_HOST = process.env.POSTGRES_HOST || 'postgres-db';
const POSTGRES_PORT = process.env.POSTGRES_PORT || '5432';
const POSTGRES_DB = process.env.FLIGHT_DB || 'flight_db';

const pool = new Pool({
  user: POSTGRES_USER,
  host: POSTGRES_HOST,
  database: POSTGRES_DB,
  password: POSTGRES_PASSWORD,
  port: POSTGRES_PORT,
});

// PostgreSQL接続テスト
async function testConnection() {
  try {
    const client = await pool.connect();
    await client.query('SELECT NOW()');
    client.release();
    console.log('PostgreSQL接続成功');
  } catch (error) {
    console.error('PostgreSQL接続エラー:', error);
    setTimeout(testConnection, 5000); // 5秒後にリトライ
  }
}

// ミドルウェア
app.use(cors());
app.use(express.json());

// ヘルスチェック
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'flight-node-server' });
});

// フライトをHTML形式で取得
app.get('/api/flights/html', async (req, res) => {
  try {
    // PostgreSQLからフライトを取得（日付降順）
    const result = await pool.query(`
      SELECT 
        id, 
        flight_date, 
        departure_airport, 
        arrival_airport, 
        reservation_number, 
        flight_number, 
        seat_number, 
        status,
        departure_time,
        arrival_time,
        payment_amount,
        currency,
        notes
      FROM flights 
      ORDER BY flight_date DESC
    `);

    // HTML生成
    let html = '<div class="flights-list">\n';
    result.rows.forEach(flight => {
      const flightDate = new Date(flight.flight_date).toLocaleDateString('ja-JP');
      const departureTime = flight.departure_time || '';
      const arrivalTime = flight.arrival_time || '';
      const seatNumber = flight.seat_number || '-';
      const paymentInfo = flight.payment_amount 
        ? `${flight.payment_amount} ${flight.currency || 'JPY'}`
        : '-';
      
      html += `  <div class="flight-item" data-status="${escapeHtml(flight.status)}">\n`;
      html += `    <div class="flight-header">\n`;
      html += `      <span class="flight-date">${escapeHtml(flightDate)}</span>\n`;
      html += `      <span class="flight-number">${escapeHtml(flight.flight_number)}</span>\n`;
      html += `      <span class="flight-status status-${escapeHtml(flight.status.toLowerCase())}">${escapeHtml(flight.status)}</span>\n`;
      html += `    </div>\n`;
      html += `    <div class="flight-route">\n`;
      html += `      <span class="airport">${escapeHtml(flight.departure_airport)}</span>\n`;
      html += `      <span class="arrow">→</span>\n`;
      html += `      <span class="airport">${escapeHtml(flight.arrival_airport)}</span>\n`;
      html += `    </div>\n`;
      html += `    <div class="flight-details">\n`;
      html += `      <div class="detail-item"><label>予約番号:</label> ${escapeHtml(flight.reservation_number)}</div>\n`;
      html += `      <div class="detail-item"><label>座席:</label> ${escapeHtml(seatNumber)}</div>\n`;
      if (departureTime || arrivalTime) {
        html += `      <div class="detail-item"><label>時刻:</label> ${escapeHtml(departureTime)} - ${escapeHtml(arrivalTime)}</div>\n`;
      }
      html += `      <div class="detail-item"><label>支払額:</label> ${escapeHtml(paymentInfo)}</div>\n`;
      if (flight.notes) {
        html += `      <div class="detail-item"><label>メモ:</label> ${escapeHtml(flight.notes)}</div>\n`;
      }
      html += `    </div>\n`;
      html += `  </div>\n`;
    });
    html += '</div>\n';

    res.send(html);
  } catch (error) {
    console.error('フライト取得エラー:', error);
    res.status(500).json({ error: 'フライトの取得に失敗しました' });
  }
});

// 全フライトをJSON形式で取得（確認用）
app.get('/api/flights', async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT 
        id, 
        flight_date, 
        departure_airport, 
        arrival_airport, 
        reservation_number, 
        flight_number, 
        eticket_pdf_path,
        seat_number, 
        status,
        departure_time,
        arrival_time,
        payment_amount,
        currency,
        notes,
        created_at,
        updated_at
      FROM flights 
      ORDER BY flight_date DESC
    `);
    res.json({
      success: true,
      count: result.rows.length,
      flights: result.rows
    });
  } catch (error) {
    console.error('フライト取得エラー:', error);
    res.status(500).json({ error: 'フライトの取得に失敗しました' });
  }
});

// フライトをエクスポート（JSON形式でダウンロード）
app.get('/api/flights/export', async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT 
        id, 
        flight_date, 
        departure_airport, 
        arrival_airport, 
        reservation_number, 
        flight_number, 
        eticket_pdf_path,
        seat_number, 
        status,
        departure_time,
        arrival_time,
        payment_amount,
        currency,
        notes,
        created_at,
        updated_at
      FROM flights 
      ORDER BY flight_date DESC
    `);

    const exportData = {
      version: '1.0',
      exportDate: new Date().toISOString(),
      flights: result.rows
    };

    // ファイル名生成（YYYYMMDD_HHMMSS形式）
    const now = new Date();
    const timestamp = now.toISOString()
      .replace(/[-:]/g, '')
      .replace('T', '_')
      .substring(0, 15);
    const filename = `flights_${timestamp}.json`;

    // ダウンロード用のヘッダーを設定
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.json(exportData);
    
    console.log(`エクスポート成功: ${result.rows.length}件のデータ`);
  } catch (error) {
    console.error('エクスポートエラー:', error);
    res.status(500).json({ error: 'エクスポートに失敗しました' });
  }
});

// フライトをインポート（置換モード）
app.post('/api/flights/import', async (req, res) => {
  const client = await pool.connect();
  
  try {
    const importData = req.body;

    // バリデーション
    if (!importData || !importData.flights || !Array.isArray(importData.flights)) {
      return res.status(400).json({ 
        error: '不正なデータ形式です。flightsフィールドが必要です。' 
      });
    }

    // 各レコードのバリデーション
    const requiredFields = ['flight_date', 'departure_airport', 'arrival_airport', 
                           'reservation_number', 'flight_number'];
    for (let i = 0; i < importData.flights.length; i++) {
      const item = importData.flights[i];
      
      for (const field of requiredFields) {
        if (!item[field]) {
          return res.status(400).json({ 
            error: `${i + 1}番目のレコード: ${field}フィールドが必要です` 
          });
        }
      }
    }

    // トランザクション開始
    await client.query('BEGIN');

    // 既存データを全削除
    const deleteResult = await client.query('DELETE FROM flights');
    const deletedCount = deleteResult.rowCount;

    // 新しいデータをインポート
    let importedCount = 0;
    for (const item of importData.flights) {
      await client.query(`
        INSERT INTO flights (
          flight_date, departure_airport, arrival_airport, 
          reservation_number, flight_number, eticket_pdf_path,
          seat_number, status, departure_time, arrival_time,
          payment_amount, currency, notes
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
      `, [
        item.flight_date,
        item.departure_airport,
        item.arrival_airport,
        item.reservation_number,
        item.flight_number,
        item.eticket_pdf_path || null,
        item.seat_number || null,
        item.status || 'Reserved',
        item.departure_time || null,
        item.arrival_time || null,
        item.payment_amount || null,
        item.currency || 'JPY',
        item.notes || null
      ]);
      importedCount++;
    }

    // トランザクションをコミット
    await client.query('COMMIT');

    console.log(`インポート成功: ${deletedCount}件削除、${importedCount}件インポート`);
    
    res.json({
      success: true,
      message: 'インポートが完了しました',
      deleted: deletedCount,
      imported: importedCount
    });
  } catch (error) {
    // エラーが発生した場合はロールバック
    await client.query('ROLLBACK');
    console.error('インポートエラー:', error);
    res.status(500).json({ 
      error: 'インポートに失敗しました',
      details: error.message 
    });
  } finally {
    client.release();
  }
});

// HTMLエスケープ関数
function escapeHtml(text) {
  if (text === null || text === undefined) {
    return '';
  }
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}

// サーバー起動
async function startServer() {
  await testConnection();
  
  app.listen(PORT, '0.0.0.0', () => {
    console.log(`フライトサーバーがポート${PORT}で起動しました`);
    console.log(`PostgreSQL接続先: ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}`);
  });
}

startServer();
