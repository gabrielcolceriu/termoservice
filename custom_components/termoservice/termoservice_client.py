
import logging
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

class PaymentRow:
    def __init__(self, month: str, issued_at: str, monthly_cost: float, arrears: float, penalty: float, details_url: Optional[str]):
        self.month = month
        self.issued_at = issued_at
        self.monthly_cost = monthly_cost
        self.arrears = arrears
        self.penalty = penalty
        self.details_url = details_url

class PaymentEvent:
    def __init__(self, date: str, amount: float, method: Optional[str]):
        self.date = date
        self.amount = amount
        self.method = method

@dataclass
class WaterEntry:
    month: str
    cold: Optional[float]
    hot: Optional[float]
    submitted_at: Optional[str]
    meters: Optional[list] = None
    total_consum: Optional[float] = None

class AccountSummary:
    def __init__(self, apartment_name: str, as_of: str, total_to_pay: float, items: Dict[str, float], monthly_rows: List[PaymentRow], last_payment: Optional[PaymentEvent], water_latest: Optional[WaterEntry]):
        self.apartment_name = apartment_name
        self.as_of = as_of
        self.total_to_pay = total_to_pay
        self.items = items
        self.monthly_rows = monthly_rows
        self.last_payment = last_payment
        self.water_latest = water_latest

class TermoServiceClient:
    def __init__(self, email: str, password: str, timeout: int = 20) -> None:
        self._email = email
        self._password = password
        self._timeout = timeout
        self._s = requests.Session()
        self._s.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari",
        })

    def login(self) -> None:
        r = self._s.get("https://tsiasi.ro/login", timeout=self._timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        token_el = soup.find("input", {"name": "_token"})
        if not token_el or not token_el.get("value"):
            raise RuntimeError("Nu s-a găsit token CSRF în pagina de login.")
        csrf = token_el["value"]
        payload = {"email": self._email, "password": self._password, "_token": csrf}
        self._s.post("https://tsiasi.ro/login", data=payload, allow_redirects=True, timeout=self._timeout)
        r3 = self._s.get("https://tsiasi.ro/contul-meu/sume-de-plata", timeout=self._timeout)
        if r3.status_code != 200 or ("Sume de plată" not in r3.text and "Delogare" not in r3.text):
            raise RuntimeError("Autentificarea a eșuat sau accesul la pagina protejată nu a reușit.")

    def fetch_all(self) -> List[AccountSummary]:
        payments_page = self._get("https://tsiasi.ro/contul-meu/sume-de-plata")
        soup = BeautifulSoup(payments_page, "html.parser")
        result: List[AccountSummary] = []
        for seg in soup.select(".ui.segment.accordion"):
            name_el = seg.select_one(".ap-name")
            apartment_name = name_el.get_text(strip=True) if name_el else "(necunoscut)"
            as_of_el = seg.select_one(".pay-date")
            as_of = as_of_el.get_text(strip=True) if as_of_el else ""
            items: Dict[str, float] = {}
            total_to_pay = 0.0
            for tr in seg.select("table.ui.celled.table tbody tr"):
                tds = tr.find_all("td")
                if len(tds) >= 2:
                    label = tds[0].get_text(strip=True)
                    val_txt = tds[1].get_text(strip=True)
                    items[label] = _to_float(val_txt)
            foot_th = seg.select_one("table tfoot th.price, table tfoot th:nth-of-type(2)")
            if foot_th:
                total_to_pay = _to_float(foot_th.get_text(strip=True))
            monthly_rows: List[PaymentRow] = []
            for tr in seg.select(".payments-history table tbody tr"):
                tds = tr.find_all("td")
                if len(tds) >= 6:
                    details_a = tds[5].find("a")
                    monthly_rows.append(PaymentRow(
                        month=tds[0].get_text(strip=True),
                        issued_at=tds[1].get_text(strip=True),
                        monthly_cost=_to_float(tds[2].get_text(strip=True)),
                        arrears=_to_float(tds[3].get_text(strip=True)),
                        penalty=_to_float(tds[4].get_text(strip=True)),
                        details_url=details_a["href"] if details_a and details_a.get("href") else None,
                    ))
            last_payment = self._fetch_last_payment()
            water_latest = self._fetch_water_latest()
            result.append(AccountSummary(
                apartment_name=apartment_name,
                as_of=as_of,
                total_to_pay=total_to_pay,
                items=items,
                monthly_rows=monthly_rows,
                last_payment=last_payment,
                water_latest=water_latest,
            ))
        return result

    def _fetch_last_payment(self) -> Optional[PaymentEvent]:
        html = self._get("https://tsiasi.ro/contul-meu/istoric-plati")
        s = BeautifulSoup(html, "html.parser")
        row = s.select_one("table tbody tr")
        if not row:
            return None
        tds = row.find_all("td")
        if len(tds) < 2:
            return None
        date = tds[0].get_text(strip=True)
        amount = _to_float(tds[1].get_text(strip=True))
        method = tds[2].get_text(strip=True) if len(tds) > 2 else None
        return PaymentEvent(date=date, amount=amount, method=method)

    def _fetch_water_latest(self) -> Optional[WaterEntry]:
        html = self._get("https://tsiasi.ro/contul-meu/consum-apa")
        s = BeautifulSoup(html, "html.parser")
        table = s.select_one(".consumption-history-table table") or s.select_one("table")
        if not table:
            return None
        header_meter_names: List[str] = []
        head_rows = table.select("thead tr")
        if len(head_rows) >= 2:
            for th in head_rows[1].find_all("th")[1:]:
                name = th.get_text(strip=True)
                if name:
                    header_meter_names.append(name)
        body_row = table.select_one("tbody tr")
        if not body_row:
            return None
        tds = body_row.find_all("td")
        if len(tds) < 3:
            return None
        month = tds[0].get_text(strip=True)
        values = [td.get_text(strip=True) for td in tds[1:]]
        meters: Dict[str, Dict[str, Optional[float]]] = {}
        i = 0
        m_idx = 0
        while i + 1 < len(values):
            index_val = _maybe_float(values[i])
            consum_val = _maybe_float(values[i+1])
            meter_name = header_meter_names[m_idx] if m_idx < len(header_meter_names) else f"Contor {m_idx+1}"
            meters[meter_name] = {"index": index_val, "consum": consum_val}
            i += 2
            m_idx += 1
        total_cold = sum([v.get("consum") or 0 for v in meters.values()]) if meters else None
        return WaterEntry(month=month, total_cold_consum=total_cold, submitted_at=None, meters=meters)

    def _get(self, url: str) -> str:
        r = self._s.get(url, timeout=self._timeout)
        r.raise_for_status()
        return r.text

def _to_float(txt: str) -> float:
    t = txt.replace(" Lei", "").replace("RON", "").replace(" ", "").replace(",", ".")
    try:
        return float(t)
    except Exception:
        return 0.0

def _maybe_float(txt: str) -> Optional[float]:
    t = (txt or "").replace(" ", "").replace(",", ".")
    if t == "":
        return None
    try:
        return float(t)
    except Exception:
        return None
