🏢 TermoService Iași – Home Assistant Integration

TermoService Iași este o integrare custom pentru Home Assistant
, care permite conectarea directă la portalul tsiasi.ro
 al furnizorului de servicii de administrare imobile Termo Service Iași S.A.

Integrarea extrage automat datele din contul tău de utilizator (email și parolă) și le transformă în senzori Home Assistant, oferindu-ți o imagine de ansamblu asupra cheltuielilor de întreținere și a consumului de apă rece — direct în dashboardul tău smart home.

🔧 Funcționalități

Autentificare sigură pe tsiasi.ro
 cu email + parolă.

Citire automată a:

✅ Sume de plată curente

✅ Istoric plăți

✅ Consum apă rece (Baie + Bucătărie, Index + Consum)

✅ Total consum apă (ultimul rând)

Actualizare automată la fiecare 30 de minute.

Posibilitatea de a vizualiza datele în Lovelace Dashboard sau Node-RED.

💡 Senzori disponibili
Senzor	Descriere	Unitate
sensor.apa_rece_baie_index	Index contor apă rece – baie	–
sensor.apa_rece_baie_consum	Consum apă rece – baie	m³
sensor.apa_rece_bucatarie_index	Index contor apă rece – bucătărie	–
sensor.apa_rece_bucatarie_consum	Consum apă rece – bucătărie	m³
sensor.apa_rece_total_consum	Total consum apă (ultima lună)	m³
sensor.total_de_plata	Total de plată curent (RON)	RON
sensor.ultima_plata_suma	Suma ultimei plăți	RON
sensor.ultima_plata_data	Data ultimei plăți	–
⚙️ Instalare

Copiază folderul custom_components/termoservice în directorul:

config/custom_components/termoservice


Repornește Home Assistant.

Din interfață:
Settings -> Devices & Services -> + Add Integration -> TermoService Iasi

Introdu emailul și parola de la tsiasi.ro
.

🧠 Configurare avansată

Poți modifica intervalul de actualizare din fișierul:

custom_components/termoservice/const.py


Parametru:

DEFAULT_SCAN_INTERVAL = 1800  # secunde (30 min)

🪪 Detalii tehnice

Limbaj: Python 3.11+

Framework: Home Assistant Core Integration

Dependințe: requests, beautifulsoup4

Clase principale:

TermoServiceClient – autentificare și scraping

TermoServiceCoordinator – management actualizări

Sensor Entities – senzori individuali pentru apă și plăți

🧰 Planuri viitoare

 Suport pentru mai multe apartamente per cont

 Istoric grafic complet pentru apă

 Integrare cu Utility Meter

 Auto-discovery în HACS

⚠️ Disclaimer

Această integrare nu este asociată oficial cu Termo Service Iași S.A.
Datele sunt citite exclusiv din contul tău personal de pe tsiasi.ro
 folosind metode publice (fără API).
Folosește integrarea responsabil, respectând termenii și condițiile furnizorului.

🧑‍💻 Autor
Gabriel Colceriu
📍 Iași, România
💡 Integrare dezvoltată pentru comunitatea Home Assistant România.
