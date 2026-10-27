# Property prices for the score page (phase 6): source options and plan

Status: **decided 27 October 2026: private family use, no publication** (section 4). Sections 1–3 are kept as the record of the options, and for any later decision to publish.

What the spec needs (docs/cycling-score-spec.md section 3):
- a typical price for every candidate base, including small villages;
- shown next to the score (a score-against-price chart), with a price filter whose range the user sets in their browser;
- not blended into the score;
- the source and date on the page.

Because the site and repo are public, the price data must be **publishable**, not just readable.

## 1. Sources checked

| Source | What it gives | Covers villages? | Can we publish it? |
|---|---|---|---|
| **Notaries' Statistical Portal** ([penotariado.com](https://penotariado.com/inmobiliario/en/home)), General Council of Notaries | **Actual sale prices** from notarised deeds: average €/m², size, total price and number of sales for any area drawn on a map, down to street level, by property type. Free; an account unlocks more. An API exists but isn't documented publicly. | Probably, wherever enough sales are recorded. Not yet confirmed for small villages. Covers all of Spain, including the Basque Country and Navarra. | **No, not without permission.** The terms allow "exclusive personal use" only, and forbid reproduction or public communication without the Council's "prior express authorisation". They also forbid loading the data into databases for others to query. Permission can be asked for (contact: soporte.penotariado@notariado.org). |
| **Catastro reference-value maps** ([sedecatastro.gob.es](https://www1.sedecatastro.gob.es/Accesos/SECAccvr.aspx)), from the annual market reports | Official average value modules (€/m² built) per homogeneous valuation zone, for flats, detached or semi-detached houses and terraced houses. Derived from all recorded sales. Years 2022–2027. | **Yes:** every municipality the State Catastro covers. **Not** the Basque Country or Navarra, which have their own cadastres. | Catastro reuse is allowed with the credit "© Dirección General del Catastro", and transformed products may be published. **But I found no documented download**: the maps are in the online viewer only, served by internal, undocumented map services. Bulk-querying those without asking isn't appropriate. These are official reference values: close to typical sale prices by design, but not prices. |
| **Ministry of Housing valuation statistics** (*valor tasado*), open data on [datos.gob.es](https://datos.gob.es/en/catalogo/a13002908-valor-tasado-de-la-vivienda-libre-por-municipios-de-mas-de-25-00-habitantes-total-base-20054) | Average appraised €/m², quarterly | **No:** only the roughly 300 municipalities over 25,000 people | Yes (open data). Useful only as a regional backdrop and a cross-check. |
| INE housing price index | Price index (not price levels) | No: regions only | Yes, but not useful here |
| Tax agency rental statistics | Rents and reference values | No: municipalities over 20,000 people | Yes, but not useful here |
| Idealista, Fotocasa (asking prices) | Asking prices by municipality | Partly | **No:** their terms forbid reuse and scraping. Not considered further. |

## 2. Recommendation

1. **Ask the Notaries for permission (the best data).** The request is for municipal averages only: median or mean €/m² and number of sales, by municipality and dwelling type, for the last 12–24 months. They would be shown on a free, non-commercial site with attribution. There is a precedent: Meteocat gave written permission for monthly summaries on 21 October 2026. The owner sends the request (draft below).
2. **In parallel, ask the Catastro** whether the urban value-zone maps (the annual market report's average value modules) can be downloaded in bulk, and confirm the reuse terms for publishing derived per-municipality figures. This is the fallback if the Notaries say no or don't reply. It would need a separate answer for the Basque Country and Navarra.
3. **Meanwhile, build the page parts that don't depend on the source:**
   - the price filter (range kept in the browser only, wide by default, no figure in the repo);
   - the score-against-price chart;
   - a per-base "price" slot that says "no price data" until a source is in.
   - Whichever source arrives, the build step is the same: price per municipality → each base takes its municipality's figure (or the nearest municipality with data), with the number of sales and the date shown.

What I'd like the owner to decide:
- (a) OK to send the two permission requests, from the owner's own email?
- (b) Which measure to show: **€/m²** (comparable across places) or **typical total price** (closer to "can we afford it", but mixes in house size)? Proposed: €/m² for flats and houses separately, with the total price as secondary information.
- (c) If both refuse, is personal-only use acceptable? Price data would stay in a git-ignored local file, so the filter would work only on the owner's own machine, never on the public site.

## 3. Draft permission request (Notaries), for the owner to send

> **Asunto:** Solicitud de autorización para publicar datos agregados por municipio del Portal Estadístico del Notariado
>
> Estimados señores:
>
> Mantengo un sitio web personal, gratuito y sin fines comerciales (https://stuartwmvivers.github.io/Destination-Cycling/) que compara localidades de España como posibles lugares de residencia vacacional para ciclistas: clima, puertos de montaña cercanos, carreteras tranquilas y acceso a aeropuertos.
>
> Me gustaría mostrar, junto a cada municipio, una referencia del precio de la vivienda. Solicito su autorización para publicar, citando siempre al Portal Estadístico del Notariado como fuente, únicamente **datos agregados por municipio**: precio medio (o mediano) por m² y número de compraventas, por tipo de vivienda (piso / unifamiliar), de los últimos 12 a 24 meses. No publicaría datos de operaciones individuales ni a nivel de calle.
>
> Si fuera posible, también les agradecería saber si disponen de estos datos en un fichero o servicio, y a partir de qué número de compraventas se ofrece el dato de un municipio pequeño.
>
> Muchas gracias por su atención.
>
> Un saludo,
> [name]

(English gist: a free, non-commercial personal site comparing places in Spain as cycling holiday-home bases. It asks permission to publish only municipal aggregates — average or median €/m² and number of sales, by flat or house, for the last 12–24 months — always credited. It asks whether a file or service exists, and what the minimum number of sales is for a small municipality to have a figure.)

A similar, shorter request to the Catastro would ask whether the urban value-zone maps (*módulos de valor medio* of the *Informe Anual del Mercado Inmobiliario*) can be downloaded, and whether per-municipality summaries derived from them may be published with the credit "© Dirección General del Catastro".

## 4. What was decided and built (27 October 2026)

- **Owner's decision:** the site is for personal and family use at present, so no permission requests. Property prices stay **private**:
  - never in the public repo or on GitHub Pages;
  - family access later through a login-protected copy (planned: Cloudflare Pages with Cloudflare Access, the owner's account).
  - The permission drafts above are only for a later decision to publish.
- **Source:** the notaries' portal map, the **average price per m² of notarised sales over the last 12 months, per municipality**.
  - It needs no account and covers small villages wherever there were enough sales; otherwise it says "Without info".
  - A free account (the owner's) adds the number of sales, flats vs houses and trends, but only **50 detailed queries a month** (`basic.number.monthly.queries`).
  - The site uses Google's invisible reCAPTCHA. Lookups are made through the normal search box at a person's pace, and stop if it ever challenges.
- **Scripts in `pipeline/score/`:**
  - `municipalities.py`: OSM municipal boundaries (8,274) and the municipality of every base (320 s);
  - `price_shortlist.py`: the best 150 areas under the default settings (one per 15 km) plus the validation places, giving **165 municipalities**;
  - `price_join.py`: joins the private prices onto the bases. A base takes its own municipality's price only, never a neighbour's.
- **Private files (`data/private/`, git-ignored):**
  - `prices.json`: the lookups (portal name, province, €/m², date checked);
  - `score_prices.json`: the join.
- **Build:** `python build/build_site.py --private` adds `data/score/spain-prices.json` and a "private copy" footer to the score page. The normal build never does. Two guards:
  - the private build refuses to run in GitHub Actions;
  - `tests/data_check.py` fails in GitHub Actions if a price file is in `_site`.
- **Page (private copy only):**
  - a price range filter (remembered in the browser only; no budget in the repo) and an "only bases with a price" switch;
  - €/m² in the top-bases and known-places tables;
  - a price line in each breakdown;
  - a score-against-price chart, one dot per municipality.
- **First lookups (27 Oct 2026):**
  - 156 of the 165 municipalities have a figure, covering 735 bases including all the top areas.
  - 8 had too few sales ("Without info"): Palol de Revardit, Montmajor, Sant Ferriol, El Brull, Castellfollit del Boix, La Nou de Berguedà, Puntallana, Nogales.
  - L'Esquirol wasn't found on the portal.
- **Caveats:**
  - a municipal average mixes flats and houses, and a coastal resort with its inland villages (Vélez-Málaga includes Torre del Mar);
  - a few figures look low for their towns (one Murcia town in particular) and should be checked with the detailed statistics before relying on them.
  - No portal figures are written in this repo, in documents or code. They live in `data/private/` only.
- **To refresh or extend:** rerun `price_shortlist.py [N]` after the weather completes, look up the new municipalities, then `price_join.py` and the private build.
