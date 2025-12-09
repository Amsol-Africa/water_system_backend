# integrations/stronpower_service.py
from __future__ import annotations
from typing import Any, Dict, Tuple, Optional, List, Union
import requests
import os

JsonLike = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


class StronpowerService:
    """
    Wrapper around Stronpower vending APIs, based on their manual.

    We support:
    - QueryMeterInfo
    - QueryMeterCredit
    - VendingMeter
    - ClearCredit
    - ClearTamper
    """

    # Allow override via env, but default to the documented hosts
    BASE_URL_NEWV = os.getenv(
        "STRONPOWER_BASE_URL",
        "http://www.server-newv.stronpower.com/api",
    )
    BASE_URL_API = os.getenv(
        "STRONPOWER_DIRECT_BASE_URL",
        "http://www.server-api.stronpower.com/api",
    )  # for VendingMeterDirectly etc

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout

    # -------------------------
    # Helper: perform POST
    # -------------------------
    def _post(
        self, url: str, payload: Dict[str, Any]
    ) -> Tuple[bool, Optional[JsonLike], Optional[str]]:
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            try:
                data = r.json()
            except ValueError:
                return False, None, "Invalid JSON response from Stronpower"
            return True, data, None
        except requests.RequestException as e:
            return False, None, str(e)

    # -------------------------
    # 2.6 QueryMeterInfo
    # -------------------------
    def query_meter_info(
        self, client_credentials: Dict[str, str], meter_id: str
    ) -> Tuple[bool, Optional[JsonLike], Optional[str]]:
        """
        Calls: POST /api/QueryMeterInfo

        Body:
        {
          "CompanyName": "DicksonAbukal",
          "UserName": "Prepaid",
          "PassWord": "147369",
          "MeterId": "58000185726"
        }
        """
        url = f"{self.BASE_URL_NEWV}/QueryMeterInfo"
        payload = {
            "CompanyName": client_credentials["company_name"],
            "UserName": client_credentials["username"],
            "PassWord": client_credentials["password"],
            "MeterId": meter_id,
        }
        return self._post(url, payload)

    # -------------------------
    # 2.7 QueryMeterCredit
    # -------------------------
    def query_meter_credit(
        self, client_credentials: Dict[str, str], meter_id: str
    ) -> Tuple[bool, Optional[JsonLike], Optional[str]]:
        """
        Calls: POST /api/QueryMeterCredit
        """
        url = f"{self.BASE_URL_NEWV}/QueryMeterCredit"
        payload = {
            "CompanyName": client_credentials["company_name"],
            "UserName": client_credentials["username"],
            "PassWord": client_credentials["password"],
            "MeterId": meter_id,
        }
        return self._post(url, payload)

    # -------------------------
    # 2.8 VendingMeter (normal)
    # This is the method your IssueTokenView expects:
    #   success, token_value, error = stronpower.vending_meter(...)
    # -------------------------
    def vending_meter(
        self,
        client_credentials: Dict[str, str],
        meter_id: str,
        amount,
        is_vend_by_unit: bool,
        customer_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Calls: POST /api/VendingMeter

        Body example (vending by unit):
        {
          "CompanyName": "your company name",
          "UserName": "your user name",
          "PassWord": "your password",
          "MeterID": "58100000007",
          "is_vend_by_unit": "true",
          "Amount": "1700"
        }

        Returns: (success, token_value, error_message)
        """
        url = f"{self.BASE_URL_NEWV}/VendingMeter"
        payload: Dict[str, Any] = {
            "CompanyName": client_credentials["company_name"],
            "UserName": client_credentials["username"],
            "PassWord": client_credentials["password"],
            "MeterID": meter_id,
            "is_vend_by_unit": "true" if is_vend_by_unit else "false",
            "Amount": str(amount),
        }

        # Optional: some APIs also accept CustomerId
        if customer_id:
            payload["CustomerId"] = customer_id

        ok, data, error = self._post(url, payload)
        if not ok:
            return False, None, error

        # Try to extract a token from the response
        token_value: Optional[str] = None

        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                token_value = (
                    first.get("Token")
                    or first.get("TokenNo")
                    or first.get("TokenNo1")
                    or str(first)
                )
            else:
                token_value = str(first)
        elif isinstance(data, dict):
            token_value = (
                data.get("Token")
                or data.get("TokenNo")
                or data.get("TokenNo1")
                or str(data)
            )
        else:
            token_value = str(data)

        return True, token_value, None

    # Optional: keep your old simple method as a thin alias if you still use it anywhere
    def vend(
        self,
        credentials: Dict[str, str],
        meter_id: str,
        amount: str,
        is_vend_by_unit: bool = True,
    ) -> Tuple[bool, Optional[JsonLike], Optional[str]]:
        """
        Legacy helper; not used by tokens/views.py, but kept for completeness.
        """
        return self._post(
            f"{self.BASE_URL_NEWV}/VendingMeter",
            {
                "CompanyName": credentials["company_name"],
                "UserName": credentials["username"],
                "PassWord": credentials["password"],
                "MeterID": meter_id,
                "is_vend_by_unit": "true" if is_vend_by_unit else "false",
                "Amount": str(amount),
            },
        )

    # -------------------------
    # 2.1 ClearCredit
    # NOTE: signature matches ClearCreditView:
    #   stronpower.clear_credit(client_credentials=..., meter_id=..., customer_id=...)
    # -------------------------
    def clear_credit(
        self,
        client_credentials: Dict[str, str],
        meter_id: str,
        customer_id: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Calls: POST /api/ClearCredit

        Body:
        {
          "CompanyName": "...",
          "UserName": "...",
          "PassWord": "...",
          "CustomerId": "0001",
          "METER_ID": "58100000007"
        }
        """
        url = f"{self.BASE_URL_NEWV}/ClearCredit"
        payload = {
            "CompanyName": client_credentials["company_name"],
            "UserName": client_credentials["username"],
            "PassWord": client_credentials["password"],
            "CustomerId": customer_id,
            "METER_ID": meter_id,
        }
        ok, data, error = self._post(url, payload)
        if not ok:
            return False, None, error

        token_value: Optional[str] = None
        if isinstance(data, list) and data:
            first = data[0]
            token_value = first.get("Token") if isinstance(first, dict) else str(first)
        elif isinstance(data, dict):
            token_value = data.get("Token") or str(data)
        else:
            token_value = str(data)

        return True, token_value, None

    # -------------------------
    # 2.3 ClearTamper
    # NOTE: signature matches ClearTamperView:
    #   stronpower.clear_tamper(client_credentials=..., meter_id=..., customer_id=...)
    # -------------------------
    def clear_tamper(
        self,
        client_credentials: Dict[str, str],
        meter_id: str,
        customer_id: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Calls: POST /api/ClearTamper

        Body:
        {
          "CompanyName": "...",
          "UserName": "...",
          "PassWord": "...",
          "CustomerId": "0001",
          "METER_ID": "58100000007"
        }
        """
        url = f"{self.BASE_URL_NEWV}/ClearTamper"
        payload = {
            "CompanyName": client_credentials["company_name"],
            "UserName": client_credentials["username"],
            "PassWord": client_credentials["password"],
            "CustomerId": customer_id,
            "METER_ID": meter_id,
        }
        ok, data, error = self._post(url, payload)
        if not ok:
            return False, None, error

        token_value: Optional[str] = None
        if isinstance(data, list) and data:
            first = data[0]
            token_value = first.get("Token") if isinstance(first, dict) else str(first)
        elif isinstance(data, dict):
            token_value = data.get("Token") or str(data)
        else:
            token_value = str(data)

        return True, token_value, None
