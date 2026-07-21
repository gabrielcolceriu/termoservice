# TermoService Iași — Home Assistant Integration

<p align="center">
  <img src="custom_components/termoservice/brand/icon.png" alt="TermoService" width="120">
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge" alt="HACS: Custom"></a>
  <img src="https://img.shields.io/badge/version-0.5.0-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/HA-2023.1%2B-brightgreen?style=for-the-badge&logo=home-assistant" alt="Home Assistant">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey?style=for-the-badge" alt="License">
</p>

<p align="center">
  Integrare care se conectează la portalul <strong>tsiasi.ro</strong> și aduce sumele de plată și consumul de apă direct în Home Assistant.
</p>

---

## Ce face această integrare?

Se conectează la portalul **[tsiasi.ro](https://tsiasi.ro)** al furnizorului de servicii Termo Service Iași S.A. și creează automat senzori pentru:

- 💰 **Sume de plată** — fond rulment, fond reparații, penalități, total de plată
- 💳 **Istoricul plăților** — ultimele plăți efectuate, total plătit în anul curent
- 💧 **Consum apă rece** — index și consum per contor (baie / bucătărie)
- 📅 **Perioadă trimitere index** — detectează automat fereastra de citire și permite trimiterea indexului din HA

---

## Senzori disponibili

### 💰 Sume de plată

| Senzor | Descriere | Unitate |
|--------|-----------|:-------:|
| Total de plată | Sold curent de plată | RON |
| Cost întreținere (ultima lună) | Costul din ultima factură | RON |
| Întreținere/Restanță | Debit curent | RON |
| Penalitate | Penalități acumulate | RON |
| Fond rulment | Contribuție fond rulment | RON |
| Fond reparații | Contribuție fond reparații | RON |

### 💳 Plăți

| Senzor | Descriere | Atribute |
|--------|-----------|---------|
| Ultima plată – sumă | Suma ultimei plăți (RON) | `destinatie`, `tip_plata` |
| Ultima plată – dată | Data ultimei plăți | — |
| Total plătit YYYY | Total plăți efectuate în anul curent | — |
| Istoric plăți | Număr intrări în istoric | `plati` (JSON: data, suma, destinatie, tip) |

### 💧 Apă rece

| Senzor | Descriere |
|--------|-----------|
| Apa rece – Baie – Index | Indexul contorului de la baie |
| Apa rece – Baie – Consum | Consumul baie (ultima lună înregistrată) |
| Apa rece – Bucătărie – Index | Indexul contorului de la bucătărie |
| Apa rece – Bucătărie – Consum | Consumul bucătărie (ultima lună înregistrată) |
| Apa rece – consum total | Total consum apă (suma contoare) |
| Trimitere index — perioadă | Intervalul activ de citire sau `Închisă` |

---

## Instalare

### Prin HACS (recomandat)

1. În HACS → **⋮ → Custom Repositories**
2. URL: `https://github.com/gabrielcolceriu/termoservice` — Categorie: **Integration**
3. Instalează **TermoService Iași** și repornește Home Assistant

### Manual

Copiază folderul `custom_components/termoservice/` în `config/custom_components/` și repornește HA.

---

## Configurare

### Adăugare integrare

**Settings → Devices & Services → + Add Integration → TermoService Iasi**

Introdu email-ul și parola de la [tsiasi.ro](https://tsiasi.ro).

### Interval de actualizare

**Settings → Devices & Services → TermoService → ⚙️**

Setează cât de des să fie preluate datele (30–1440 minute, implicit **120 minute**). Datele se schimbă lunar, deci o valoare mare e mai prietenoasă cu serverul furnizorului.

### Schimbare credențiale

**Settings → Devices & Services → TermoService → ⋮ → Reconfigurare**

---

## Serviciu: trimitere index apă

Disponibil în perioada de citire (de obicei 20–25 ale lunii). Valoarea senzorului **Trimitere index — perioadă** va fi diferită de `Închisă` când fereastra e activă.

```yaml
service: termoservice.trimite_index
data:
  index_baie: 612
  index_bucatarie: 663
```

---

## Cerințe

- Home Assistant 2023.1+
- Cont activ pe [tsiasi.ro](https://tsiasi.ro)
- Dependențe Python (instalate automat): `requests`, `beautifulsoup4`

---

## Disclaimer

Această integrare **nu este asociată oficial** cu Termo Service Iași S.A. Datele sunt preluate exclusiv din contul personal al utilizatorului de pe tsiasi.ro, prin metode publice (fără API oficial). Utilizează integrarea responsabil, respectând termenii și condițiile furnizorului.

---

<p align="center">
  Dezvoltat cu ❤️ de <a href="https://github.com/gabrielcolceriu">Gabriel Colceriu</a> — Iași, România
</p>
