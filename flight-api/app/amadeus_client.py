"""
Amadeus API クライアント
"""
import os
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class AmadeusClient:
    """Amadeus API との通信を管理するクライアント"""
    
    def __init__(self):
        self.api_key = os.getenv("AMADEUS_TEST_API_KEY")
        self.api_secret = os.getenv("AMADEUS_TEST_API_SECRET")
        self.base_url = "https://test.api.amadeus.com"
        self.token = None
        self.token_expires_at = None
    
    async def _get_token(self) -> str:
        """OAuth2トークンを取得"""
        if self.token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.token
        
        url = f"{self.base_url}/v1/security/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.api_secret
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            self.token = result["access_token"]
            # トークンの有効期限を設定（少し余裕を持たせる）
            expires_in = result.get("expires_in", 1799)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
            
            return self.token
    
    async def get_flight_status(
        self,
        carrier_code: str,
        flight_number: str,
        scheduled_departure_date: str,
        operational_suffix: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        On-Demand Flight Status APIでフライト情報を取得
        
        Args:
            carrier_code: 航空会社コード（2-3文字、例: "NH"）
            flight_number: フライト番号（1-4桁、例: "123"）
            scheduled_departure_date: 出発予定日（YYYY-MM-DD形式）
            operational_suffix: 運航サフィックス（オプション）
        
        Returns:
            フライトステータス情報
        """
        token = await self._get_token()
        
        url = f"{self.base_url}/v2/schedule/flights"
        params = {
            "carrierCode": carrier_code,
            "flightNumber": flight_number,
            "scheduledDepartureDate": scheduled_departure_date
        }
        if operational_suffix:
            params["operationalSuffix"] = operational_suffix
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def get_flight_order(self, flight_order_id: str) -> Dict[str, Any]:
        """
        Flight Order Management APIで予約情報を取得
        
        Args:
            flight_order_id: フライトオーダーID
        
        Returns:
            予約情報
        """
        token = await self._get_token()
        
        url = f"{self.base_url}/v1/booking/flight-orders/{flight_order_id}"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def search_airport(self, iata_code: str) -> Optional[Dict[str, Any]]:
        """
        Airport City Search APIで空港情報を取得
        
        Args:
            iata_code: 空港のIATAコード（3文字）
        
        Returns:
            空港情報（タイムゾーンオフセット含む）
        """
        token = await self._get_token()
        
        url = f"{self.base_url}/v1/reference-data/locations"
        params = {
            "subType": "AIRPORT",
            "keyword": iata_code,
            "view": "FULL"
        }
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                return data["data"][0]
            
            return None
