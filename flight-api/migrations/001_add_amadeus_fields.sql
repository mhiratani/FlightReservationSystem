-- Amadeus API連携用フィールドを追加するマイグレーション
-- 実行方法: docker exec -it flightreservationsystem-postgres-db-1 psql -U postgres -d flight_db -f /docker-entrypoint-initdb.d/001_add_amadeus_fields.sql

-- 新しいカラムを追加
ALTER TABLE flights ADD COLUMN IF NOT EXISTS gate_number VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS terminal VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS actual_departure_time TIME;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS actual_arrival_time TIME;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS delay_duration VARCHAR(20);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS aircraft_type VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS amadeus_flight_order_id VARCHAR(100);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS last_status_check TIMESTAMP;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS traveler_info JSON;

-- 確認用クエリ
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'flights'
ORDER BY ordinal_position;
