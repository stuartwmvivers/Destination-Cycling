# Interface plan: from an explorer to a family decision tool (DC-27)

Status: **thinking, 27 October 2026.** Nothing here is built. The owner's brief:
- the site must be attractive, informative, intuitive and a delight to use, with as little challenge as possible;
- family members are stakeholders in where to buy, so if they find it hard, or it doesn't tell them what they need, the site has failed.

The order of work (score-prototype-plan, "Order of work") puts this after the full weather rerun and before the family copy opens.

## 1. Where the page is today

Measured on a phone (375 px wide):
- **Controls come first.** 35 controls (presets, 7 weight sliders, flights, gate, built-up penalty) appear before anything about a place.
- **Places are a long way down.** The map starts two screens down, and the first named place, in Top bases, four screens down.
- **It's a heavy page.** 4.2 MB to download and about 1,800 words.
- **It speaks the method's language,** not a visitor's: "bases", "gate", "near climbs", "built-up penalty", weights in per cent, scores like 81.1, component bars from 0 to 1. A "Known places" table is there to validate the method, not for decisions.
- **What it does well,** and must keep:
  - the ranking is sound;
  - each place has real data behind it (climbs, monthly weather, flights, price);
  - the owner can tune everything.

The page is a good workbench for the owner. For anyone else it's an exam paper.

## 2. Who it's for and what they need to decide

- **The owner:** a cyclist who knows the method, wants to tune it and compare.
- **The family:** they share the decision and won't want to learn the method.
  - **Owner, 27 October 2026:** they all cycle a lot, and love walking and running. They holiday together and enjoy the same things.
  - **A typical day:** exercise in the morning, normally cycling in the sun. Then eating, drinking and each other's company in the sun. Meals out (or in) are a big part of a holiday.
  - **So cycling stays the headline.** Each area should also answer:
    - *Where can we walk and run?*
    - *Is it warm and sunny enough to sit outside in the afternoon and evening, month by month?*
    - *What's it like for eating out (restaurants, cafés, markets within a short walk or drive)?*

    Eating out isn't measured yet: the plan is to show it on area pages as a fact (e.g. a count of restaurants and cafés from OSM), not to score it. New factors wait until after the interface (score-prototype-plan, "Order of work").
  - Their questions are likely to be:
    - *Where should we look?*
    - *What is it like there, through the year?*
    - *How easy is it to get to from Edinburgh or Glasgow?*
    - *What would a house cost?*
    - *What kind of place is it: village, town, countryside, coast or mountains?*
    - *What's there to do for those of us who don't cycle?*
    - *Which places do the others like?*
  - **Devices (owner, 27 October 2026):** mostly an **iPad or a PC**, perhaps from a link in a message.

These needs are assumptions until the family is asked (section 6).

## 3. Principles

1. **Places first, method last.** The page opens on a short list of named areas, not on controls. The controls sit in an "Adjust" panel beside the list, and the method in an "About the score" page.
2. **Plain words, not scores.** For example:
   - "Mild winters: 17 °C highs in January, 22 dry days."
   - "Málaga airport 45 minutes away, flights from Edinburgh all year."
   - "14 big climbs within reach."
   - "Homes about €1,400/m²."

   Show ratings as words or a few filled dots, never as 79.6.
3. **One question at a time.** Each screen answers one question. Detail appears when asked for (tap to expand), never all at once.
4. **Areas, not grid points.** Group the 5 km grid into named areas (about 15 km across), each named after its main town, e.g. "Cenes de la Vega, near Granada". People think in places.
5. **iPad and PC first, phone still fine.**
   - **Layout:** a list and map side by side in landscape, stacked in portrait.
   - **Touch:** big tap targets, and no information that appears only on mouse hover (an iPad has no hover).
   - **Testing:** check in Safari as well as Chrome and Edge.
   - **Loading:** a small summary file first, so it opens quickly; the full grid loads only for the owner's explorer.
6. **Explore freely, keep favourites.** The site is a place to explore the options, not to vote (owner, 27 October 2026). Anyone can star an area to add it to their own **favourites list**. There are no votes or shared notes.
7. **Honest and calm.** Say plainly what each figure is and where it's weak, e.g. "prices are a municipal average", in one line next to the figure, not in a methods essay.
8. **Delight comes from clarity and craft.**
   - Good type and generous space.
   - One consistent colour for "good".
   - Smooth map moves.
   - A monthly weather strip you can read at a glance.
   - Photographs if licensing allows: Wikimedia Commons, credited.

## 4. Proposed structure

**Home: "Places worth a look"**
- One line on what the site is, then about 12 area cards, best first.
- **Each card shows:**
  - the name, with a photo or map snippet;
  - a one-line character: "Village in the hills above Granada";
  - four plain facts: winter weather, flights, cycling, price;
  - a star to add it to your favourites.
- **What matters to you:** quick presets in plain words, e.g. "Warmest winters", "Easiest flights", "Best cycling", "Quietest". They lead into the full controls in Adjust.
- **A small map:** it shows the cards' areas and highlights a card when you tap it.

**Area page (one per area): the dossier**
- **The facts:**
  - **Weather:** the year in a 12-month strip (temperature, dry days, rideable days), using the existing climate pages' data where there is a station.
  - **Getting there:** airports, drive times and which months have direct flights from Edinburgh or Glasgow.
  - **Cycling:** the climbs, with a simple list and their links, plus quiet roads, gravel and walking in words.
  - **Homes:** €/m² with its date and caveat, and links that open property searches for that municipality on the usual portals (links only, no copied listings).
  - **Setting:** village, town or countryside, built-up share and what's nearby.
- **Links:** Google Maps and Street View, to look around.

**Explore the map (owner, 28 October 2026):** a separate page for browsing at leisure, in addition to Places. It changes nothing on the other pages.
- **The colours:** every 5 km point in Spain, coloured from *Limited* to *Excellent*. The bands are the bottom 20%, then up to 50%, 80% and 95%, then the top 5% of points that meet the must-haves. Points that don't meet them are grey.
- **Shared settings:** it uses the same "Priorities" choices and Adjust panel as the list, so the colours always match.
- **Getting around:** "Go to" buttons jump to Málaga & Granada, Costa Blanca, Girona, the Pyrenees, Mallorca and the Canaries.
- **Tapping a spot** shows its name, band, climbs, riding days, airport, price (in the private copy) and strengths, with a link to the nearest listed place.
- **On a PC,** hovering shows the name.

**Compare:** pick two or three areas and see them side by side, one row per question.

**My favourites:** the areas you've starred, ready to compare. It's a handy page to have open at a family discussion.

**Adjust (for everyone; owner, 27 October 2026: full weight controls for all):** every control the page has today, rewritten so anyone can use it without the method.
- **Plain wording.** For example:
  - a weight becomes "How much does it matter?", from *Not at all* to *A lot*, instead of a percentage;
  - the gate becomes "Must have at least 3 big climbs within reach";
  - the built-up penalty becomes "Prefer quieter surroundings";
  - flights become "Flights all year only" or "Include summer-only routes".
- **A one-line note** under each control saying what it does.
- **Instant feedback:**
  - the list and map re-order as you move a control;
  - places that move up or down are briefly marked.
- **Reset:** "Back to the agreed ranking" in one tap.
- **Placement and memory:**
  - on an iPad in landscape or a PC, the panel sits beside the list, open or closed as you like;
  - each person's settings are remembered on their device.

**About:** the method, the sources and the credits, written for a curious reader.

## 5. Technical notes

- **Favourites start in the browser:** kept on each device, with no server and nothing to set up.
  - The catch: stars made on the iPad don't appear on the PC.
  - If that matters in use, add sync later. Cloudflare Access already tells the site who is signed in, so a small Cloudflare Worker with its free KV store can keep each person's list, with no extra accounts. It needs one more key permission (Workers and KV edit).
- **Areas and their plain-language facts would be precomputed** in `score_export.py` (a small `areas.json`). The full 4 MB grid would load only for the map's detail view; re-ranking areas uses the small file.
- **The existing climate pages** (spain-coast and others) would feed the area pages' weather strip, so there's one site with one style.

## 6. How to get it right: ask, sketch, test

1. **Ask the family first.** Send three or four short questions:
   - what they'd want to know about a place;
   - whether they cycle;
   - what would put them off.

   This takes them five minutes. A draft is to be agreed with the owner, and the owner sends it.
2. **Sketch:** a clickable mock-up of the home page, one area page and the shortlist, using real data for a few areas. The owner tries it.
3. **Watch one person use it.** Ask a family member to do three tasks on their iPad or PC while the owner watches without helping:
   - find the three best places for winter;
   - open one and say whether you'd like it;
   - add it to your favourites.

   Note where they hesitate. Ten minutes of this beats any amount of guessing.
4. **Build**, then repeat step 3 once before the family copy opens.

**Success measure:** a family member who has never seen the site can do those three tasks on an iPad or PC, unaided, in under five minutes, and says they'd come back to it.

## 7. Open questions for the owner

- Is the owner happy to ask the family the short questions in section 6, and to run the ten-minute test?
