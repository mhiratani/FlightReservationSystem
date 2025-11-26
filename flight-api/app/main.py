from fastapi import FastAPI, HTTPException, status, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sql_delete
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date, time
from decimal import Decimal
import os
import json
import shutil
import base64
import anthropic

from .database import get_db, init_db
from .models import Flight

app = FastAPI(
    title="フライト予約管理API",
    description="フライト予約と搭乗記録を管理するAPI",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydanticモデル
class FlightCreate(BaseModel):
    flight_date: date
    departure_airport: str
    arrival_airport: str
    reservation_number: str
    flight_number: str
    eticket_pdf_path: Optional[str] = None
    seat_number: Optional[str] = None
    status: str = "Reserved"
    departure_time: Optional[time] = None
    arrival_time: Optional[time] = None
    notes: Optional[str] = None
    payment_amount: Optional[Decimal] = None
    currency: Optional[str] = "JPY"

class FlightUpdate(BaseModel):
    flight_date: Optional[date] = None
    departure_airport: Optional[str] = None
    arrival_airport: Optional[str] = None
    reservation_number: Optional[str] = None
    flight_number: Optional[str] = None
    eticket_pdf_path: Optional[str] = None
    seat_number: Optional[str] = None
    status: Optional[str] = None
    departure_time: Optional[time] = None
    arrival_time: Optional[time] = None
    notes: Optional[str] = None
    payment_amount: Optional[Decimal] = None
    currency: Optional[str] = None

class FlightResponse(BaseModel):
    id: int
    flight_date: date
    departure_airport: str
    arrival_airport: str
    reservation_number: str
    flight_number: str
    eticket_pdf_path: Optional[str]
    seat_number: Optional[str]
    status: str
    departure_time: Optional[time]
    arrival_time: Optional[time]
    notes: Optional[str]
    payment_amount: Optional[Decimal]
    currency: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# エクスポート・インポート機能のPydanticモデル
class ExportData(BaseModel):
    """エクスポートデータモデル"""
    version: str
    exportDate: str
    flights: List[dict]

class ImportData(BaseModel):
    """インポートデータモデル"""
    version: Optional[str] = None
    exportDate: Optional[str] = None
    flights: List[dict]

class ImportResponse(BaseModel):
    """インポートレスポンスモデル"""
    success: bool
    message: str
    deleted: int
    imported: int

class PDFImportResponse(BaseModel):
    """PDFインポートレスポンスモデル"""
    success: bool
    message: str
    flights: List[dict]

@app.on_event("startup")
async def startup_db_client():
    """アプリケーション起動時にデータベースを初期化"""
    await init_db()

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"message": "フライト予約管理API - /docs でAPIドキュメントを確認できます"}

@app.get("/api/flights", response_model=List[FlightResponse])
async def get_flights(db: AsyncSession = Depends(get_db)):
    """フライト一覧を取得（日付降順）"""
    result = await db.execute(
        select(Flight).order_by(Flight.flight_date.desc())
    )
    flights = result.scalars().all()
    return flights

@app.get("/api/flights/export")
async def export_flights(db: AsyncSession = Depends(get_db)):
    """フライトをJSON形式でエクスポート（ダウンロード）"""
    try:
        # 全てのフライトを取得
        result = await db.execute(
            select(Flight).order_by(Flight.flight_date.desc())
        )
        flights = result.scalars().all()
        
        # エクスポートデータを構築
        export_data = {
            "version": "1.0",
            "exportDate": datetime.utcnow().isoformat() + "Z",
            "flights": [
                {
                    "id": f.id,
                    "flight_date": f.flight_date.isoformat(),
                    "departure_airport": f.departure_airport,
                    "arrival_airport": f.arrival_airport,
                    "reservation_number": f.reservation_number,
                    "flight_number": f.flight_number,
                    "eticket_pdf_path": f.eticket_pdf_path,
                    "seat_number": f.seat_number,
                    "status": f.status,
                    "departure_time": f.departure_time.isoformat() if f.departure_time else None,
                    "arrival_time": f.arrival_time.isoformat() if f.arrival_time else None,
                    "notes": f.notes,
                    "payment_amount": float(f.payment_amount) if f.payment_amount else None,
                    "currency": f.currency,
                    "created_at": f.created_at.isoformat(),
                    "updated_at": f.updated_at.isoformat()
                }
                for f in flights
            ]
        }
        
        # ファイル名生成（YYYYMMDD_HHMMSS形式）
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = f"flights_{timestamp}.json"
        
        # JSONレスポンスを作成
        json_content = json.dumps(export_data, ensure_ascii=False, indent=2)
        
        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"エクスポートに失敗しました: {str(e)}"
        )

@app.post("/api/flights/import", response_model=ImportResponse)
async def import_flights(import_data: ImportData, db: AsyncSession = Depends(get_db)):
    """フライトをJSON形式でインポート（置換モード）"""
    try:
        # バリデーション
        if not import_data.flights or not isinstance(import_data.flights, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="flightsフィールドは配列である必要があります"
            )
        
        # 各レコードのバリデーション
        required_fields = ["flight_date", "departure_airport", "arrival_airport", 
                          "reservation_number", "flight_number"]
        for i, item in enumerate(import_data.flights, 1):
            for field in required_fields:
                if field not in item:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"{i}番目のレコード: {field}フィールドが必要です"
                    )
        
        # トランザクション内で処理
        # 既存データを全削除
        delete_result = await db.execute(sql_delete(Flight))
        deleted_count = delete_result.rowcount
        await db.flush()
        
        # 新しいデータをインポート
        imported_count = 0
        for item in import_data.flights:
            db_flight = Flight(
                flight_date=item["flight_date"],
                departure_airport=item["departure_airport"],
                arrival_airport=item["arrival_airport"],
                reservation_number=item["reservation_number"],
                flight_number=item["flight_number"],
                eticket_pdf_path=item.get("eticket_pdf_path"),
                seat_number=item.get("seat_number"),
                status=item.get("status", "Reserved"),
                departure_time=item.get("departure_time"),
                arrival_time=item.get("arrival_time"),
                notes=item.get("notes"),
                payment_amount=item.get("payment_amount"),
                currency=item.get("currency", "JPY")
            )
            db.add(db_flight)
            imported_count += 1
        
        # コミット
        await db.commit()
        
        return ImportResponse(
            success=True,
            message="インポートが完了しました",
            deleted=deleted_count,
            imported=imported_count
        )
    
    except HTTPException:
        # HTTPExceptionはそのまま再送出
        await db.rollback()
        raise
    except Exception as e:
        # その他のエラー
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"インポートに失敗しました: {str(e)}"
        )

@app.get("/api/flights/{flight_id}", response_model=FlightResponse)
async def get_flight(flight_id: int, db: AsyncSession = Depends(get_db)):
    """特定のフライトを取得"""
    result = await db.execute(
        select(Flight).where(Flight.id == flight_id)
    )
    flight = result.scalar_one_or_none()
    
    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="フライトが見つかりません"
        )
    
    return flight

@app.post("/api/flights", response_model=FlightResponse, status_code=status.HTTP_201_CREATED)
async def create_flight(flight: FlightCreate, db: AsyncSession = Depends(get_db)):
    """新しいフライトを作成"""
    db_flight = Flight(
        flight_date=flight.flight_date,
        departure_airport=flight.departure_airport,
        arrival_airport=flight.arrival_airport,
        reservation_number=flight.reservation_number,
        flight_number=flight.flight_number,
        eticket_pdf_path=flight.eticket_pdf_path,
        seat_number=flight.seat_number,
        status=flight.status,
        departure_time=flight.departure_time,
        arrival_time=flight.arrival_time,
        notes=flight.notes,
        payment_amount=flight.payment_amount,
        currency=flight.currency
    )
    db.add(db_flight)
    await db.commit()
    await db.refresh(db_flight)
    
    return db_flight

@app.put("/api/flights/{flight_id}", response_model=FlightResponse)
async def update_flight(
    flight_id: int,
    flight: FlightUpdate,
    db: AsyncSession = Depends(get_db)
):
    """フライトを更新"""
    result = await db.execute(
        select(Flight).where(Flight.id == flight_id)
    )
    db_flight = result.scalar_one_or_none()
    
    if db_flight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="フライトが見つかりません"
        )
    
    # 更新するフィールドのみを適用
    update_data = flight.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_flight, key, value)
    
    await db.commit()
    await db.refresh(db_flight)
    
    return db_flight

@app.delete("/api/flights/{flight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flight(flight_id: int, db: AsyncSession = Depends(get_db)):
    """フライトを削除"""
    result = await db.execute(
        select(Flight).where(Flight.id == flight_id)
    )
    db_flight = result.scalar_one_or_none()
    
    if db_flight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="フライトが見つかりません"
        )
    
    await db.execute(
        sql_delete(Flight).where(Flight.id == flight_id)
    )
    await db.commit()
    
    return None

@app.post("/api/flights/{flight_id}/upload-eticket")
async def upload_eticket(
    flight_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """EチケットPDFをアップロード（同じ予約番号のすべてのフライトに紐づける）"""
    # フライトの存在確認
    result = await db.execute(
        select(Flight).where(Flight.id == flight_id)
    )
    db_flight = result.scalar_one_or_none()
    
    if db_flight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="フライトが見つかりません"
        )
    
    # ファイル形式チェック
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDFファイルのみアップロード可能です"
        )
    
    # 予約番号を取得
    reservation_number = db_flight.reservation_number
    
    # 同じ予約番号を持つすべてのフライトを取得
    result = await db.execute(
        select(Flight).where(Flight.reservation_number == reservation_number)
    )
    related_flights = result.scalars().all()
    
    # 古いPDFファイルのパスを取得（削除用）
    old_pdf_path = None
    if related_flights and related_flights[0].eticket_pdf_path:
        old_pdf_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            related_flights[0].eticket_pdf_path
        )
    
    # ファイル名生成（予約番号ベース）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"eticket_{reservation_number}_{timestamp}.pdf"
    file_path = os.path.join("pdfs", safe_filename)
    full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)
    
    # ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # ファイルを保存
    try:
        with open(full_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ファイルの保存に失敗しました: {str(e)}"
        )
    
    # 同じ予約番号を持つすべてのフライトを更新
    updated_count = 0
    for flight in related_flights:
        flight.eticket_pdf_path = file_path
        updated_count += 1
    
    await db.commit()
    
    # 古いPDFファイルを削除
    if old_pdf_path and os.path.exists(old_pdf_path):
        try:
            os.remove(old_pdf_path)
        except Exception as e:
            # ファイル削除に失敗しても続行（ログに記録するのみ）
            print(f"警告: 古いPDFファイルの削除に失敗しました: {str(e)}")
    
    return {
        "success": True,
        "message": f"Eチケットをアップロードし、{updated_count}件のフライトに紐づけました",
        "file_path": file_path,
        "updated_flights": updated_count,
        "reservation_number": reservation_number
    }

@app.post("/api/flights/import-from-file", response_model=PDFImportResponse)
async def import_from_file(file: UploadFile = File(...)):
    """PDFまたは画像からフライト情報を抽出（Claude API使用）"""
    # ファイル形式チェック
    file_extension = file.filename.lower().split('.')[-1]
    supported_formats = {
        'pdf': ('document', 'application/pdf'),
        'png': ('image', 'image/png'),
        'jpg': ('image', 'image/jpeg'),
        'jpeg': ('image', 'image/jpeg'),
        'webp': ('image', 'image/webp'),
        'gif': ('image', 'image/gif')
    }
    
    if file_extension not in supported_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"サポートされていないファイル形式です。対応形式: {', '.join(supported_formats.keys())}"
        )
    
    content_type, media_type = supported_formats[file_extension]
    
    try:
        # ファイルを読み込んでBase64エンコード
        file_content = await file.read()
        file_base64 = base64.standard_b64encode(file_content).decode("utf-8")
        
        # APIキーを環境変数から取得
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ANTHROPIC_API_KEYが設定されていません"
            )
        
        # Claude APIクライアントを初期化
        client = anthropic.Anthropic(api_key=api_key)
        
        # ファイルタイプに応じてcontentブロックを構築
        if content_type == 'document':
            file_content_block = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": file_base64
                }
            }
        else:  # image
            file_content_block = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": file_base64
                }
            }
        
        # プロンプトを作成（日本語）
        prompt = """このEチケット（PDFまたは画像）から、以下の情報を抽出してください。
1つのEチケットに複数の便が含まれている場合は、すべての便の情報を抽出してください。

抽出する情報：
- flight_date: 搭乗日付 (YYYY-MM-DD形式)
- flight_number: フライト番号 (例: NH123)
- departure_airport: 出発空港 (3レターコード、例: NRT)
- arrival_airport: 到着空港 (3レターコード、例: HND)
- departure_time: 出発時刻 (HH:MM形式、例: 09:30)
- arrival_time: 到着時刻 (HH:MM形式、例: 11:00)
- reservation_number: 予約番号
- seat_number: 座席番号 (例: 12A)
- payment_amount: 支払額 (数値のみ)
- currency: 通貨 (例: JPY, USD)

以下のJSON形式で返してください（他のテキストは一切含めず、JSONのみを返してください）：
{
  "flights": [
    {
      "flight_date": "2025-12-01",
      "flight_number": "NH123",
      "departure_airport": "NRT",
      "arrival_airport": "HND",
      "departure_time": "09:30",
      "arrival_time": "11:00",
      "reservation_number": "ABC123",
      "seat_number": "12A",
      "payment_amount": 25000,
      "currency": "JPY",
      "status": "Reserved"
    }
  ]
}

情報が見つからない場合はnullを設定してください。"""
        
        # Claude APIを呼び出し
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        file_content_block,
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        # レスポンスからテキストを抽出
        response_text = message.content[0].text
        
        # JSONをパース
        try:
            # レスポンスからJSONを抽出（マークダウンのコードブロックを除去）
            json_text = response_text.strip()
            if json_text.startswith("```"):
                # コードブロックを除去
                lines = json_text.split("\n")
                json_text = "\n".join(lines[1:-1]) if len(lines) > 2 else json_text
            
            flight_data = json.loads(json_text)
            
            if "flights" not in flight_data or not isinstance(flight_data["flights"], list):
                raise ValueError("レスポンスに'flights'配列が含まれていません")
            
            return PDFImportResponse(
                success=True,
                message=f"{len(flight_data['flights'])}件のフライト情報を抽出しました",
                flights=flight_data["flights"]
            )
            
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"JSONのパースに失敗しました: {str(e)}\nレスポンス: {response_text}"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"レスポンスの形式が不正です: {str(e)}"
            )
            
    except anthropic.APIError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Claude APIエラー: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ファイルの処理中にエラーが発生しました: {str(e)}"
        )

@app.get("/api/pdfs/{filename}")
async def get_pdf(filename: str):
    """PDFファイルを取得"""
    # ファイル名のセキュリティチェック（パストラバーサル対策）
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なファイル名です"
        )
    
    # PDFファイルのパスを構築
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pdfs", filename)
    
    # ファイルの存在確認
    if not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDFファイルが見つかりません"
        )
    
    # PDFファイルを返す（ブラウザでインライン表示）
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )

@app.get("/api/flights/{flight_id}/eticket")
async def get_flight_eticket(flight_id: int, db: AsyncSession = Depends(get_db)):
    """フライトに紐づくEチケットPDFを取得"""
    # フライトの存在確認
    result = await db.execute(
        select(Flight).where(Flight.id == flight_id)
    )
    db_flight = result.scalar_one_or_none()
    
    if db_flight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="フライトが見つかりません"
        )
    
    # PDFパスの確認
    if not db_flight.eticket_pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="このフライトにはEチケットが紐づいていません"
        )
    
    # PDFファイルのフルパスを構築
    pdf_full_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        db_flight.eticket_pdf_path
    )
    
    # ファイルの存在確認
    if not os.path.exists(pdf_full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDFファイルが見つかりません"
        )
    
    # ファイル名を抽出
    filename = os.path.basename(db_flight.eticket_pdf_path)
    
    # PDFファイルを返す（ブラウザでインライン表示）
    return FileResponse(
        path=pdf_full_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )

@app.get("/admin")
async def admin_page():
    """管理画面を表示"""
    admin_html_path = os.path.join(os.path.dirname(__file__), "static", "admin.html")
    if os.path.exists(admin_html_path):
        return FileResponse(admin_html_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="管理画面が見つかりません"
        )
