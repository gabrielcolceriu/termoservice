
from datetime import date

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
from .coordinator import TermoServiceCoordinator

def _slug(text: str) -> str:
    trans = str.maketrans({"ă":"a","â":"a","î":"i","ș":"s","ş":"s","ț":"t","ţ":"t",
                           "Ă":"A","Â":"A","Î":"I","Ș":"S","Ş":"S","Ț":"T","Ţ":"T"})
    return (text.translate(trans)
                .lower()
                .replace("/", "_")
                .replace("*", "")
                .replace(" ", "_")
                .strip("_"))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add_entities) -> None:
    coordinator: TermoServiceCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for idx, acc in enumerate(coordinator.data or []):
        base_unique = f"{entry.entry_id}_{idx}"
        entities.extend([
            TermoTotalToPaySensor(coordinator, base_unique, acc_idx=idx),
            TermoLastMonthCostSensor(coordinator, base_unique, acc_idx=idx),
            TermoUnpaidCountSensor(coordinator, base_unique, acc_idx=idx),
            TermoLastPaymentAmountSensor(coordinator, base_unique, acc_idx=idx),
            TermoLastPaymentDateSensor(coordinator, base_unique, acc_idx=idx),
            TermoTotalPaidCurrentYearSensor(coordinator, base_unique, acc_idx=idx),
            TermoPaymentHistorySensor(coordinator, base_unique, acc_idx=idx),
            TermoWaterColdLatestSensor(coordinator, base_unique, acc_idx=idx),
        ])
        entities.extend([
            TermoWaterSubmissionSensor(coordinator, base_unique, acc_idx=idx),
        ])
        for item_key in (acc.items or {}):
            entities.append(TermoDebitItemSensor(
                coordinator, f"{base_unique}_item_{_slug(item_key)}", acc_idx=idx, item_key=item_key,
            ))
        meters = (acc.water_latest.meters if acc.water_latest else {}) or {}
        for mname, data in list(meters.items())[:4]:
            norm = mname.lower().replace(" ", "_")
            entities.append(TermoWaterMeterIndexSensor(coordinator, f"{base_unique}_index_{norm}", acc_idx=idx, meter_name=mname))
            entities.append(TermoWaterMeterConsumSensor(coordinator, f"{base_unique}_consum_{norm}", acc_idx=idx, meter_name=mname))
    add_entities(entities)

class _BaseTermoSensor(SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator: TermoServiceCoordinator, unique_base: str, acc_idx: int) -> None:
        self.coordinator = coordinator
        self._acc_idx = acc_idx
        self._attr_unique_id = f"{unique_base}_{self.__class__.__name__}"
    @property
    def device_info(self) -> DeviceInfo:
        acc = (self.coordinator.data or [])[self._acc_idx]
        return DeviceInfo(identifiers={(DOMAIN, f"acc_{self._acc_idx}")}, name=f"TermoService – {acc.apartment_name}", manufacturer="TermoService Iași", model="Web portal")
    @property
    def available(self) -> bool:
        return getattr(self.coordinator, "last_update_success", True)
    async def async_update(self) -> None:
        await self.coordinator.async_request_refresh()

class TermoTotalToPaySensor(_BaseTermoSensor):
    _attr_icon = "mdi:cash-clock"

    @property
    def name(self) -> str:
        return "Total de plată"
    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        return round(acc.total_to_pay, 2)
    @property
    def unit_of_measurement(self) -> str:
        return "RON"

class TermoLastMonthCostSensor(_BaseTermoSensor):
    _attr_icon = "mdi:radiator"

    @property
    def name(self) -> str:
        return "Cost întreținere (ultima lună)"
    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        if not acc.monthly_rows:
            return None
        return round(acc.monthly_rows[0].monthly_cost, 2)
    @property
    def unit_of_measurement(self) -> str:
        return "RON"

class TermoUnpaidCountSensor(_BaseTermoSensor):
    _attr_icon = "mdi:format-list-numbered"

    @property
    def name(self) -> str:
        return "Număr luni listate"
    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        return len(acc.monthly_rows)

class TermoLastPaymentAmountSensor(_BaseTermoSensor):
    _attr_icon = "mdi:cash-check"

    @property
    def name(self) -> str:
        return "Ultima plată – sumă"
    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        return None if not acc.last_payment else round(acc.last_payment.amount, 2)
    @property
    def unit_of_measurement(self) -> str:
        return "RON"
    @property
    def extra_state_attributes(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        if not acc.last_payment:
            return {}
        return {
            "destinatie": acc.last_payment.destination,
            "tip_plata": acc.last_payment.method,
        }

class TermoLastPaymentDateSensor(_BaseTermoSensor):
    _attr_icon = "mdi:calendar-check"

    @property
    def name(self) -> str:
        return "Ultima plată – dată"
    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        return None if not acc.last_payment else acc.last_payment.date

class TermoWaterColdLatestSensor(_BaseTermoSensor):
    _attr_icon = "mdi:water-pump"

    @property
    def name(self) -> str:
        return "Apa rece – consum total (ultimul rand)"
    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        return None if not acc.water_latest else acc.water_latest.total_consum


class TermoWaterMeterIndexSensor(_BaseTermoSensor):
    def __init__(self, coordinator, unique_base, acc_idx, meter_name):
        
        super().__init__(coordinator, unique_base, acc_idx)
        self._meter = meter_name
    def _clean(self, s: str) -> str:
        x = (s or "").strip()
        if x.lower().endswith(" ct"):
            x = x[:-3].strip()
        trans = str.maketrans({"ă":"a","â":"a","î":"i","ș":"s","ş":"s","ț":"t","ţ":"t","Ă":"A","Â":"A","Î":"I","Ș":"S","Ş":"S","Ț":"T","Ţ":"T"})
        x = x.translate(trans)
        if x.lower() == "bucatarie":
            x = "Bucatarie"
        if x.lower() == "baie":
            x = "Baie"
        return x
    _attr_icon = "mdi:counter"

    @property
    def name(self) -> str:
        m = self._clean(self._meter)
        return f"Apa rece – {m} – Index"
    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        meters = (acc.water_latest.meters if acc.water_latest else {}) or {}
        data = meters.get(self._meter, {})
        return data.get("index")

class TermoWaterMeterConsumSensor(_BaseTermoSensor):
    def __init__(self, coordinator, unique_base, acc_idx, meter_name):
        super().__init__(coordinator, unique_base, acc_idx)
        self._meter = meter_name
    def _clean(self, s: str) -> str:
        x = (s or "").strip()
        if x.lower().endswith(" ct"):
            x = x[:-3].strip()
        trans = str.maketrans({"ă":"a","â":"a","î":"i","ș":"s","ş":"s","ț":"t","ţ":"t","Ă":"A","Â":"A","Î":"I","Ș":"S","Ş":"S","Ț":"T","Ţ":"T"})
        x = x.translate(trans)
        if x.lower() == "bucatarie":
            x = "Bucatarie"
        if x.lower() == "baie":
            x = "Baie"
        return x
    _attr_icon = "mdi:water"

    @property
    def name(self) -> str:
        m = self._clean(self._meter)
        return f"Apa rece – {m} – Consum"
    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        meters = (acc.water_latest.meters if acc.water_latest else {}) or {}
        data = meters.get(self._meter, {})
        return data.get("consum")


class TermoTotalPaidCurrentYearSensor(_BaseTermoSensor):
    _attr_icon = "mdi:cash-multiple"

    @property
    def name(self) -> str:
        return f"Total plătit {date.today().year}"

    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        year = str(date.today().year)
        return round(sum(p.amount for p in (acc.payments or []) if p.date[-4:] == year), 2)

    @property
    def unit_of_measurement(self) -> str:
        return "RON"


class TermoPaymentHistorySensor(_BaseTermoSensor):
    _attr_icon = "mdi:history"

    @property
    def name(self) -> str:
        return "Istoric plăți"

    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        return len(acc.payments or [])

    @property
    def extra_state_attributes(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        return {
            "plati": [
                {
                    "data": p.date,
                    "suma": p.amount,
                    "destinatie": p.destination,
                    "tip": p.method,
                }
                for p in (acc.payments or [])
            ]
        }


class TermoWaterSubmissionSensor(_BaseTermoSensor):
    @property
    def name(self) -> str:
        return "Trimitere index — perioadă"

    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        if not acc.water_latest or not acc.water_latest.submission_period:
            return "Închisă"
        return acc.water_latest.submission_period

    @property
    def extra_state_attributes(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        open_ = acc.water_latest.submission_open if acc.water_latest else False
        return {"deschisa": open_}

    @property
    def icon(self) -> str:
        acc = (self.coordinator.data or [])[self._acc_idx]
        open_ = acc.water_latest.submission_open if acc.water_latest else False
        return "mdi:water-check" if open_ else "mdi:water-off"


class TermoDebitItemSensor(_BaseTermoSensor):
    def __init__(self, coordinator, unique_base, acc_idx, item_key):
        super().__init__(coordinator, unique_base, acc_idx)
        self._item_key = item_key

    @property
    def name(self) -> str:
        return self._item_key.rstrip("*").strip()

    @property
    def icon(self) -> str:
        key = self._item_key.lower()
        if any(w in key for w in ("caldura", "caldură", "incalzire", "încălzire", "termie")):
            return "mdi:radiator"
        if any(w in key for w in ("apa calda", "apă caldă", "acm")):
            return "mdi:water-boiler"
        if any(w in key for w in ("apa rece", "apă rece")):
            return "mdi:water"
        if any(w in key for w in ("gunoi", "deseuri", "deșeuri", "salubr")):
            return "mdi:trash-can-outline"
        if any(w in key for w in ("ascensor", "lift")):
            return "mdi:elevator-passenger"
        if any(w in key for w in ("electric", "energie", "curent")):
            return "mdi:lightning-bolt"
        if "gaz" in key:
            return "mdi:gas-burner"
        if any(w in key for w in ("fond", "reparatii", "reparații")):
            return "mdi:tools"
        if any(w in key for w in ("administr", "admin")):
            return "mdi:account-wrench"
        return "mdi:clipboard-list-outline"

    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        val = (acc.items or {}).get(self._item_key, 0.0)
        return round(val, 2)

    @property
    def unit_of_measurement(self) -> str:
        return "RON"


