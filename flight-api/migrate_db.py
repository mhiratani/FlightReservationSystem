"""
データベースマイグレーションスクリプト
Amadeus API連携用フィールドを追加

実行方法:
docker exec -it flightreservationsystem-flight-api-1 python migrate_db.py
"""
import asyncio
import os
from sqlalchemy import text
from app.database import engine, AsyncSessionLocal


async def run_migration():
    """マイグレーションを実行"""
    print("🔄 マイグレーション開始...")
    
    async with AsyncSessionLocal() as session:
        try:
            # 既存のカラムをチェックして、存在しない場合のみ追加
            migrations = [
                ("gate_number", "ALTER TABLE flights ADD COLUMN gate_number VARCHAR(10)"),
                ("terminal", "ALTER TABLE flights ADD COLUMN terminal VARCHAR(10)"),
                ("actual_departure_time", "ALTER TABLE flights ADD COLUMN actual_departure_time TIME"),
                ("actual_arrival_time", "ALTER TABLE flights ADD COLUMN actual_arrival_time TIME"),
                ("delay_duration", "ALTER TABLE flights ADD COLUMN delay_duration VARCHAR(20)"),
                ("aircraft_type", "ALTER TABLE flights ADD COLUMN aircraft_type VARCHAR(10)"),
                ("amadeus_flight_order_id", "ALTER TABLE flights ADD COLUMN amadeus_flight_order_id VARCHAR(100)"),
                ("last_status_check", "ALTER TABLE flights ADD COLUMN last_status_check TIMESTAMP"),
                ("traveler_info", "ALTER TABLE flights ADD COLUMN traveler_info JSON"),
            ]
            
            for column_name, alter_sql in migrations:
                # カラムが存在するかチェック
                check_sql = text("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='flights' AND column_name=:column_name
                    )
                """)
                result = await session.execute(check_sql, {"column_name": column_name})
                exists = result.scalar()
                
                if not exists:
                    print(f"  ✅ カラム '{column_name}' を追加中...")
                    await session.execute(text(alter_sql))
                else:
                    print(f"  ⏭️  カラム '{column_name}' は既に存在します")
            
            await session.commit()
            print("\n✅ マイグレーション完了!")
            
            # テーブル構造を表示
            print("\n📋 現在のテーブル構造:")
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'flights'
                ORDER BY ordinal_position
            """))
            
            print(f"{'カラム名':<30} {'型':<20} {'NULL許可'}")
            print("-" * 60)
            for row in result:
                nullable = "YES" if row.is_nullable == "YES" else "NO"
                print(f"{row.column_name:<30} {row.data_type:<20} {nullable}")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ エラーが発生しました: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_migration())
