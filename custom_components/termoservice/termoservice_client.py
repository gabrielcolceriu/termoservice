from __future__ import annotations

import json
import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


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
    meters: Optional[Dict[str, Dict[str, Optional[float]]]] = None
    total_consum: Optional[float] = None
    submission_open: bool = False
    submission_period: Optional[str] = None


class AccountSummary:
    def __init__(self, apartment_name: str, as_of: str, total_to_pay: float, items: Dict[str, float],
                 monthly_rows: List[PaymentRow], last_payment: Optional[PaymentEvent], water_latest: Optional[WaterEntry]):
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
        self._s.headers.update({"User-Agent": _UA})

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

            lw = self._call_livewire_load(payments_page)
            if lw:
                total_to_pay = lw["total_to_pay"]
                items = lw["items"]
                monthly_rows = lw["monthly_rows"]
                as_of = lw["as_of"]
            else:
                total_to_pay = 0.0
                items = {}
                monthly_rows = []
                as_of = ""

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

    def _call_livewire_load(self, page_html: str) -> Optional[dict]:
        snapshot_match = re.search(r'wire:snapshot="([^"]*)"', page_html)
        lw_url_match = re.search(r'(livewire-[a-f0-9]+)/update', page_html)
        if not snapshot_match or not lw_url_match:
            _LOGGER.debug("Nu s-a găsit componentă Livewire în pagina de plăți.")
            return None

        try:
            snapshot = json.loads(snapshot_match.group(1).replace("&quot;", '"'))
            lw_url = f"https://tsiasi.ro/{lw_url_match.group(0)}"
            xsrf = urllib.parse.unquote(self._s.cookies.get("XSRF-TOKEN", ""))

            payload = json.dumps({
                "components": [{
                    "snapshot": json.dumps(snapshot),
                    "updates": {},
                    "calls": [{"path": "", "method": "loadData", "params": []}],
                }]
            })

            r = self._s.post(
                lw_url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Livewire": "true",
                    "X-XSRF-TOKEN": xsrf,
                    "Accept": "application/json",
                    "Origin": "https://tsiasi.ro",
                    "Referer": "https://tsiasi.ro/contul-meu/sume-de-plata",
                },
                timeout=self._timeout,
            )
            r.raise_for_status()

            comp = r.json()["components"][0]
            snap_data = json.loads(comp["snapshot"])["data"]
            total_to_pay = float(snap_data.get("totalDePlata") or 0)

            lw_soup = BeautifulSoup(comp.get("effects", {}).get("html", ""), "html.parser")

            # "Datorii la data de DD.MM.YYYY"
            as_of = ""
            for el in lw_soup.find_all(string=re.compile(r"la data de")):
                as_of = el.strip()
                break

            items: Dict[str, float] = {}
            for tr in lw_soup.select("table.small-table tbody tr"):
                tds = tr.find_all("td")
                if len(tds) >= 2:
                    items[tds[0].get_text(strip=True)] = _to_float(tds[1].get_text(strip=True))

            monthly_rows: List[PaymentRow] = []
            for tr in lw_soup.select("table.large-table tbody tr"):
                tds = tr.find_all("td")
                if len(tds) >= 5:
                    details_a = tds[5].find("a") if len(tds) > 5 else None
                    monthly_rows.append(PaymentRow(
                        month=tds[0].get_text(strip=True),
                        issued_at=tds[1].get_text(strip=True),
                        monthly_cost=_to_float(tds[2].get_text(strip=True)),
                        arrears=_to_float(tds[3].get_text(strip=True)),
                        penalty=_to_float(tds[4].get_text(strip=True)),
                        details_url=details_a["href"] if details_a and details_a.get("href") else None,
                    ))

            return {"total_to_pay": total_to_pay, "items": items, "monthly_rows": monthly_rows, "as_of": as_of}

        except Exception as exc:
            _LOGGER.warning("Eroare la apelul Livewire: %s", exc)
            return None

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

        # Detectăm dacă tabelul e încărcat via Livewire
        has_livewire = bool(re.search(r'wire:snapshot', html))
        has_table = bool(re.search(r'<table', html, re.IGNORECASE))
        _LOGGER.debug("consum-apa: has_livewire=%s, has_table=%s, html_len=%s", has_livewire, has_table, len(html))

        # Dacă tabelul e gol dar există componentă Livewire, apelăm loadData
        lw_url_match = re.search(r'(livewire-[a-f0-9]+)/update', html)
        snapshot_match = re.search(r'wire:snapshot="([^"]*)"', html)
        if lw_url_match and snapshot_match and not has_table:
            try:
                snapshot = json.loads(snapshot_match.group(1).replace("&quot;", '"'))
                lw_url = f"https://tsiasi.ro/{lw_url_match.group(0)}"
                xsrf = urllib.parse.unquote(self._s.cookies.get("XSRF-TOKEN", ""))
                payload = json.dumps({
                    "components": [{
                        "snapshot": json.dumps(snapshot),
                        "updates": {},
                        "calls": [{"path": "", "method": "loadData", "params": []}],
                    }]
                })
                r = self._s.post(lw_url, data=payload, headers={
                    "Content-Type": "application/json",
                    "X-Livewire": "true",
                    "X-XSRF-TOKEN": xsrf,
                    "Accept": "application/json",
                    "Origin": "https://tsiasi.ro",
                    "Referer": "https://tsiasi.ro/contul-meu/consum-apa",
                }, timeout=self._timeout)
                r.raise_for_status()
                comp = r.json()["components"][0]
                html = comp.get("effects", {}).get("html", "") or html
                _LOGGER.debug("consum-apa Livewire html_len=%s", len(html))
            except Exception as exc:
                _LOGGER.warning("Eroare Livewire consum-apa: %s", exc)

        s = BeautifulSoup(html, "html.parser")
        all_tables = s.find_all("table")
        _LOGGER.debug("consum-apa: %s tabele găsite", len(all_tables))

        # Tabel 0 = formular trimitere; Tabel 1 = istoric consum
        if len(all_tables) < 2:
            _LOGGER.debug("consum-apa: lipsește tabelul de istoric")
            return None
        table = all_tables[1]

        all_rows = table.find_all("tr")

        # Găsim rândul cu numele contoarelor: cel cu cei mai mulți th colspan>=2
        # (row "Baie ct / Bucatarie", nu row "Apa rece" care are colspan unic)
        head_meters = []
        best_count = 0
        for tr in all_rows:
            ths = tr.find_all("th")
            colspan_ths = [th for th in ths if int(th.get("colspan", 1)) >= 2 and th.get_text(strip=True)]
            if len(colspan_ths) > best_count:
                best_count = len(colspan_ths)
                head_meters = [th.get_text(strip=True) for th in colspan_ths]
        _LOGGER.debug("consum-apa: head_meters=%s", head_meters)

        # Primul rând cu td = primul rând de date
        data_rows = [tr for tr in all_rows if tr.find("td")]
        if not data_rows:
            return None

        tds = data_rows[0].find_all("td")
        if not tds:
            return None

        month = tds[0].get_text(strip=True)
        meters: Dict[str, Dict[str, Optional[float]]] = {}
        pos = 1
        mcount = max(0, (len(tds) - 1) // 2)
        for i in range(mcount):
            idx_val = tds[pos].get_text(strip=True) if pos < len(tds) else ""
            cns_val = tds[pos + 1].get_text(strip=True) if (pos + 1) < len(tds) else ""
            pos += 2
            raw_name = head_meters[i] if i < len(head_meters) else f"Contor {i + 1}"
            mname = _norm(raw_name)
            meters[mname] = {
                "index": _maybe_float(idx_val),
                "consum": _maybe_float(cns_val),
            }

        try:
            total_consum = sum((v.get("consum") or 0.0) for v in meters.values())
        except Exception:
            total_consum = None

        # Perioadă trimitere index — căutăm în textul decodat (BeautifulSoup decodează &ndash;, &nbsp;)
        submission_open = False
        submission_period = None
        page_text = s.get_text(" ", strip=True).replace('\xa0', ' ')
        period_match = re.search(r"(\d{2}\.\d{2}\.\d{4})\s*[-–—]\s*(\d{2}\.\d{2}\.\d{4})", page_text)
        if not period_match:
            # Fallback: decodăm manual entitățile HTML din sursa brută
            raw_dec = html.replace('&ndash;', '–').replace('&mdash;', '—').replace('&nbsp;', ' ')
            period_match = re.search(r"(\d{2}\.\d{2}\.\d{4})\s*[-–—]\s*(\d{2}\.\d{2}\.\d{4})", raw_dec)
        if period_match:
            start_str, end_str = period_match.group(1), period_match.group(2)
            try:
                start = datetime.strptime(start_str, "%d.%m.%Y").date()
                end = datetime.strptime(end_str, "%d.%m.%Y").date()
                submission_open = start <= date.today() <= end
                submission_period = f"{start_str} - {end_str}"
            except ValueError:
                pass

        return WaterEntry(
            month=month,
            cold=total_consum,
            hot=None,
            submitted_at=None,
            meters=meters,
            total_consum=total_consum,
            submission_open=submission_open,
            submission_period=submission_period,
        )

    def submit_water_index(self, index_baie: float, index_bucatarie: float) -> None:
        html = self._get("https://tsiasi.ro/contul-meu/consum-apa")
        s = BeautifulSoup(html, "html.parser")

        if not re.search(r"\d{2}\.\d{2}\.\d{4}\s*[-–]\s*\d{2}\.\d{2}\.\d{4}", html):
            raise RuntimeError("Nu e perioadă de trimitere index.")

        # Încearcă Livewire
        snapshot_matches = list(re.finditer(r'wire:snapshot="([^"]*)"', html))
        lw_url_match = re.search(r'(livewire-[a-f0-9]+)/update', html)

        if snapshot_matches and lw_url_match:
            for snap_m in snapshot_matches:
                try:
                    snapshot = json.loads(snap_m.group(1).replace("&quot;", '"'))
                    snap_data = snapshot.get("data", {})
                    # Detectăm cheia pentru index din proprietățile componentei
                    _LOGGER.debug("Livewire snapshot data keys: %s", list(snap_data.keys()))
                except Exception:
                    continue

            # Construim mapping meter_name → valoare index
            meter_map = {"Baie": index_baie, "Bucatarie": index_bucatarie}
            snapshot = json.loads(snapshot_matches[0].group(1).replace("&quot;", '"'))
            snap_data = snapshot.get("data", {})

            # Detectăm cheile din snapshot care corespund indexurilor
            updates: Dict[str, float] = {}
            for key in snap_data:
                kl = key.lower()
                if "baie" in kl or "bath" in kl:
                    updates[key] = index_baie
                elif "bucatar" in kl or "kitchen" in kl or "buc" in kl:
                    updates[key] = index_bucatarie

            if not updates:
                _LOGGER.warning("Nu s-au detectat chei Livewire pentru contoare. Chei disponibile: %s", list(snap_data.keys()))
                raise RuntimeError("Nu s-au putut mapa câmpurile formularului. Verificați logurile.")

            lw_url = f"https://tsiasi.ro/{lw_url_match.group(0)}"
            xsrf = urllib.parse.unquote(self._s.cookies.get("XSRF-TOKEN", ""))
            payload = json.dumps({
                "components": [{
                    "snapshot": json.dumps(snapshot),
                    "updates": updates,
                    "calls": [{"path": "", "method": "save", "params": []}],
                }]
            })
            r = self._s.post(
                lw_url, data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Livewire": "true",
                    "X-XSRF-TOKEN": xsrf,
                    "Accept": "application/json",
                    "Origin": "https://tsiasi.ro",
                    "Referer": "https://tsiasi.ro/contul-meu/consum-apa",
                },
                timeout=self._timeout,
            )
            r.raise_for_status()
            _LOGGER.info("Index apă trimis: Baie=%s, Bucatarie=%s", index_baie, index_bucatarie)
            return

        # Fallback: form HTML clasic
        form = s.find("form")
        if not form:
            raise RuntimeError("Nu s-a găsit formularul de trimitere index.")
        action = form.get("action") or "https://tsiasi.ro/contul-meu/consum-apa"
        if not action.startswith("http"):
            action = f"https://tsiasi.ro{action}"
        data: Dict[str, str] = {}
        for inp in form.find_all("input"):
            name = inp.get("name", "")
            if name:
                data[name] = inp.get("value", "")
        # Mapăm indexurile în câmpurile text
        for inp in form.find_all("input", {"type": ["text", "number"]}):
            name = (inp.get("name") or "").lower()
            placeholder = (inp.get("placeholder") or "").lower()
            label_for = inp.get("id", "")
            label_el = s.find("label", {"for": label_for})
            label_text = (label_el.get_text(strip=True) if label_el else "").lower()
            if any(x in name + placeholder + label_text for x in ["baie", "bath"]):
                data[inp["name"]] = str(index_baie)
            elif any(x in name + placeholder + label_text for x in ["bucatar", "buc", "kitchen"]):
                data[inp["name"]] = str(index_bucatarie)
        _LOGGER.debug("Trimitere form: action=%s, data=%s", action, data)
        r = self._s.post(action, data=data, allow_redirects=True, timeout=self._timeout)
        r.raise_for_status()
        _LOGGER.info("Index apă trimis (form): Baie=%s, Bucatarie=%s", index_baie, index_bucatarie)

    def _get(self, url: str) -> str:
        r = self._s.get(url, timeout=self._timeout)
        r.raise_for_status()
        return r.text


def _norm(x: str) -> str:
    x = x.strip()
    if x.lower().endswith(" ct"):
        x = x[:-3].strip()
    trans = str.maketrans({"ă": "a", "â": "a", "î": "i", "ș": "s", "ş": "s", "ț": "t", "ţ": "t",
                           "Ă": "A", "Â": "A", "Î": "I", "Ș": "S", "Ş": "S", "Ț": "T", "Ţ": "T"})
    x = x.translate(trans)
    x_low = x.lower()
    if x_low == "baie":
        return "Baie"
    if x_low == "bucatarie":
        return "Bucatarie"
    return x[:1].upper() + x[1:] if x else x


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
