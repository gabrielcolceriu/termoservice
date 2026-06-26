
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
from .coordinator import TermoServiceCoordinator

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
            TermoWaterColdLatestSensor(coordinator, base_unique, acc_idx=idx),
            TermoWaterColdTotalSensor(coordinator, base_unique, acc_idx=idx),
            TermoWaterSubmittedAtSensor(coordinator, base_unique, acc_idx=idx),
        ])
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
    @property
    def name(self) -> str:
        return "Număr luni listate"
    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        return len(acc.monthly_rows)

class TermoLastPaymentAmountSensor(_BaseTermoSensor):
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

class TermoLastPaymentDateSensor(_BaseTermoSensor):
    @property
    def name(self) -> str:
        return "Ultima plată – dată"
    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        return None if not acc.last_payment else acc.last_payment.date

class TermoWaterColdLatestSensor(_BaseTermoSensor):
    @property
    def name(self) -> str:
        return "Apa rece – consum total (ultimul rand)"
    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        return None if not acc.water_latest else acc.water_latest.total_consum


class TermoWaterSubmittedAtSensor(_BaseTermoSensor):
    @property
    def name(self) -> str:
        return "Consum apă – transmis la"
    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        return None if not acc.water_latest else acc.water_latest.submitted_at

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


class TermoWaterColdTotalSensor(_BaseTermoSensor):
    @property
    def name(self) -> str:
        return "Apa rece – Total – Consum"
    @property
    def native_value(self):
        acc = (self.coordinator.data or [])[self._acc_idx]
        return None if not acc.water_latest else acc.water_latest.total_consum
