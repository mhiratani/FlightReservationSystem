"""
空港タイムゾーン管理モジュール
"""
import json
import os
from datetime import datetime
from typing import Optional, Dict
import anthropic


class TimezoneManager:
    """空港のタイムゾーン情報を管理"""
    
    def __init__(self, data_file: str = "data/airport_timezones.json"):
        self.data_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            data_file
        )
        self.data = self._load_data()
        
    def _load_data(self) -> Dict:
        """JSONファイルからデータをロード"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "version": "1.0.0",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "airports": {}
        }
    
    def _save_data(self):
        """JSONファイルにデータを保存"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        self.data["last_updated"] = datetime.utcnow().isoformat() + "Z"
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    async def get_timezone_offset(
        self, 
        iata_code: str,
        amadeus_client
    ) -> Optional[str]:
        """
        空港のタイムゾーンオフセットを取得
        
        戦略:
        1. ローカルキャッシュから取得
        2. Amadeus APIで取得してキャッシュ
        3. Claude APIに問い合わせ（フォールバック）
        
        Args:
            iata_code: 空港のIATAコード（3文字）
            amadeus_client: AmadeusClientのインスタンス
        
        Returns:
            タイムゾーンオフセット（例: "+09:00"）
        """
        # 1. キャッシュチェック
        if iata_code in self.data.get("airports", {}):
            return self.data["airports"][iata_code]["timezone_offset"]
        
        # 2. Amadeus APIで取得
        try:
            offset = await self._fetch_from_amadeus(iata_code, amadeus_client)
            if offset:
                return offset
        except Exception as e:
            print(f"Amadeus API error for {iata_code}: {e}")
        
        # 3. Claude APIでフォールバック
        try:
            offset = await self._fetch_from_claude(iata_code)
            if offset:
                return offset
        except Exception as e:
            print(f"Claude API error for {iata_code}: {e}")
        
        return None
    
    async def _fetch_from_amadeus(
        self, 
        iata_code: str,
        amadeus_client
    ) -> Optional[str]:
        """Amadeus Airport City Search APIから取得"""
        location = await amadeus_client.search_airport(iata_code)
        
        if location and location.get("timeZoneOffset"):
            # キャッシュに保存
            airport_info = {
                "iata_code": location.get("iataCode"),
                "city_name": location.get("address", {}).get("cityName"),
                "city_code": location.get("address", {}).get("cityCode"),
                "country_code": location.get("address", {}).get("countryCode"),
                "timezone_offset": location.get("timeZoneOffset"),
                "timezone_name": None,  # Amadeusでは取得不可
                "source": "amadeus",
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
            
            if "airports" not in self.data:
                self.data["airports"] = {}
            
            self.data["airports"][iata_code] = airport_info
            self._save_data()
            
            return location.get("timeZoneOffset")
        
        return None
    
    async def _fetch_from_claude(self, iata_code: str) -> Optional[str]:
        """Claude APIからタイムゾーンを推測"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""空港コード「{iata_code}」のタイムゾーンオフセットを教えてください。

回答は以下のJSON形式のみで返してください（他のテキストは含めないでください）：
{{
  "iata_code": "{iata_code}",
  "city_name": "都市名",
  "country_code": "国コード（2文字）",
  "timezone_offset": "+09:00",
  "timezone_name": "Asia/Tokyo"
}}

タイムゾーンオフセットは"+HH:MM"または"-HH:MM"の形式で返してください。"""
        
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text.strip()
        
        # JSONをパース
        try:
            # コードブロックを除去
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
            
            result = json.loads(response_text)
            
            # キャッシュに保存
            airport_info = {
                "iata_code": result.get("iata_code"),
                "city_name": result.get("city_name"),
                "city_code": None,
                "country_code": result.get("country_code"),
                "timezone_offset": result.get("timezone_offset"),
                "timezone_name": result.get("timezone_name"),
                "source": "claude",
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
            
            if "airports" not in self.data:
                self.data["airports"] = {}
            
            self.data["airports"][iata_code] = airport_info
            self._save_data()
            
            return result.get("timezone_offset")
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}, response: {response_text}")
            return None
    
    def get_cached_timezone(self, iata_code: str) -> Optional[str]:
        """キャッシュからタイムゾーンオフセットを取得（非同期なし）"""
        if iata_code in self.data.get("airports", {}):
            return self.data["airports"][iata_code]["timezone_offset"]
        return None
