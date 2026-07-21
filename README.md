# TermoService Iași — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Integrare custom pentru Home Assistant care conectează direct la portalul **tsiasi.ro** al furnizorului de servicii Termo Service Iași S.A.

---

## Funcționalități

- Autentificare sigură pe tsiasi.ro cu email + parolă
- **Reconfigurare din UI** — schimbi email/parolă fără să ștergi integrarea
- **Interval de refresh configurabil** din UI (30–1440 minute, default 120 min)
- Senzori actualizați automat

---

## Senzori disponibili

### Sume de plată
| Senzor | Descriere | Unitate |
|--------|-----------|---------|
| Total de plată | Sold curent | RON |
| Cost întreținere (ultima lună) | Costul lunii curente | RON |
| Întreținere/Restanță | Debit curent | RON |
| Penalitate | Penalități acumulate | RON |
| Fond rulment | Fond rulment | RON |
| Fond reparații | Fond reparații | RON |

### Plăți
| Senzor | Descriere |
|--------|-----------|
| Ultima plată – sumă | Suma ultimei plăți (RON) + atribute: destinație, tip plată |
| Ultima plată – dată | Data ultimei plăți |
| Total plătit YYYY | Total plăți efectuate în anul curent (RON) |
| Istoric plăți | Număr plăți + atribut JSON cu istoricul complet |

### Apă rece
| Senzor | Descriere |
|--------|-----------|
| Apa rece – Baie – Index | Indexul contorului de la baie |
| Apa rece – Baie – Consum | Consumul baie (ultima lună) |
| Apa rece – Bucătărie – Index | Indexul contorului de la bucătărie |
| Apa rece – Bucătărie – Consum | Consumul bucătărie (ultima lună) |
| Apa rece – consum total | Total consum apă (ultima lună) |
| Trimitere index — perioadă | Intervalul activ de trimitere (sau „Închisă") |

---

## Instalare via HACS

1. În HACS → **Custom Repositories** adaugă: `https://github.com/gabrielcolceriu/termoservice`
2. Categorie: **Integration**
3. Instalează **TermoService Iași**
4. Repornește Home Assistant
5. **Settings → Devices & Services → + Add Integration → TermoService Iasi**
6. Introdu email-ul și parola de la tsiasi.ro

---

## Instalare manuală

Copiază folderul `custom_components/termoservice` în directorul `config/custom_components/`, repornește HA și adaugă integrarea din UI.

---

## Configurare

### Interval de refresh
**Settings → Devices & Services → TermoService → ⚙️ → Interval de actualizare**

Default: 120 minute. Range: 30–1440 minute.

### Schimbare credențiale
**Settings → Devices & Services → TermoService → ⋮ → Reconfigurare**

---

## Serviciu: trimitere index apă

Disponibil în perioada de citire (de obicei 20–25 ale lunii):

```yaml
service: termoservice.trimite_index
data:
  index_baie: 612
  index_bucatarie: 663
```

---

## Disclaimer

Această integrare nu este asociată oficial cu Termo Service Iași S.A. Datele sunt citite exclusiv din contul personal de pe tsiasi.ro folosind metode publice. Folosește integrarea responsabil, respectând termenii și condițiile furnizorului.

---

**Autor:** Gabriel Colceriu — Iași, România
