# Sponsorenkompass

> **The sponsor around the corner: found, justified, approached.**

Sponsorenkompass shows local clubs in three minutes how much sponsorship potential they have: **which businesses in their region are a good fit** and **what offer** to approach them with. Every suggestion is backed by sources, the outreach is ready to send, and existing sponsors are managed in the same place.

Built on 7 November 2026 at the **Cursor × Sandbox Founders Hackathon** in the CREATORS space, Stuttgart.

| | |
|---|---|
| 🎬 Pitch + demo video | _link coming_ |
| 🖥️ Live demo | _link coming_ |
| 📊 Pitch deck | [Google Slides](https://docs.google.com/presentation/d/1p4gav7rx0arVGWb5EWd1qgWBckvdj517CTxpvdoi-bI/edit) |

---

## The problem

Finding sponsors means knocking on doors. Volunteers with no sales experience work from business directories and gut feeling, send generic mass letters and rarely hear back. Many clubs don't even know what they could offer a sponsor, or what it is worth. Most local businesses are not on any sponsorship platform.

**Who it is for:** board members, treasurers and sponsorship leads of small and mid-sized clubs, plus support associations (Fördervereine) and other non-profits. Sports federations and district sports associations as a sales channel.

## Two sides, one match

| Supply: what does the club have? | Demand: who fits? |
|---|---|
| Inventory from the [sponsorship catalogue](docs/sponsoring-katalog.md): perimeter boards, jerseys, social media, tournaments, apprenticeship partnerships and more | Businesses nearby from OpenStreetMap, researched with exa.ai |
| What is free, what is taken, what is it worth? | Local engagement, past sponsorships, closeness to the club's audience |

Sponsorenkompass brings both together: **every candidate gets a recommended package**, e.g. "Bäckerei Müller, 1.2 km, already supports the town festival: perimeter board plus a stand at the club festival, approx. €600 per season".

## User flow

1. **Enter the website (30 s):** website URL and town. The AI reads the club's site.
2. **Confirm the profile (1–2 min):** sports, teams, league, events and detected sponsors are pre-filled. The board corrects them, answers a few questions (members, spectators, goal) and ticks off its inventory. **Existing sponsors** are uploaded as a list ([CSV template](docs/vorlage-bestandssponsoren.csv)) or added by hand.
3. **Potential analysis (the wow moment):** one number for the untapped potential per season, the catalogue with free packages and guide prices, the top candidates on a map and the gaps ("you have no bank, no bakery, no car dealer").
4. **Open a candidate:** three reasons with source links, the recommended package, a ready letter, a call script and an email for after the first contact.
5. **Manage sponsors:** pipeline (new → contacted → meeting → yes/no) and existing sponsors with package, amount and term. CSV export.

**Every statement has a source.** Ratings are based only on texts that were actually found. If little was found, the tool shows low confidence instead of inventing reasons. Prices are labelled as guide values.

## How we differ

| Offering | What it does | What is missing |
|---|---|---|
| findasponsor, Motivation4Teams | Marketplace: clubs create profiles, businesses search | Only reaches businesses that sign up themselves |
| Clubvermarktung | Manages sponsors, contracts, invoices | No active search for new sponsors |
| Agencies (e.g. HeySponsor) | Personal sponsor acquisition | Too expensive for small clubs |
| Business directories, Google Maps | List of businesses | No reasoning, no offer, no outreach |
| **Sponsorenkompass** | **Potential analysis, active search with sources, matching package, ready outreach** | Contracts and invoices are left to existing tools (today; see [Potential](#potential)) |

---

## Features (as of 7 Nov 2026)

**Done**
- [x] Landing page with sign-up for the waiting list and pilot clubs
- [x] Onboarding **from the website alone**: profile, teams, league, events
- [x] **Sports ground** instead of the imprint address as the search centre (imprints often list private addresses)
- [x] Existing sponsors from text **and from logos** (Gemini reads the logos on the sponsor page), CSV import
- [x] Offer inventory from the sponsorship catalogue
- [x] Businesses nearby (Google Places, OpenStreetMap as fallback), pre-filter, gaps by industry
- [x] Research with exa.ai, score 0–100 with three reasons and source links, recommended package with guide price
- [x] Potential analysis: untapped potential per season, free packages, assumptions disclosed
- [x] Analysis runs in the background – no waiting, optional email when everything is done
- [x] Outreach: letter, phone script, email for after the first contact
- [x] **Sponsor CRM**: edit existing sponsors, contact, status, amount, term, history, follow-ups, expiring contracts
- [x] **Assets**: perimeter boards, jerseys, social media … with quantity, assignments to sponsors, price, term
- [x] Turn a candidate into a sponsor after a yes
- [x] **Accounts** to current security standards (see Security); analysis only after sign-in
- [x] CSV export

**Next**
- [ ] "Similar to your best sponsor"
- [ ] Detect industry conflicts (e.g. two car dealers when exclusivity was promised)
- [ ] Sponsorship brochure as PDF
- [ ] Email confirmation, password reset, two-factor/passkeys

**Deliberately not (yet):** automated mass mailing. Payments, contracts and invoices are not part of the hackathon build; how they could follow is described under [Potential](#potential).

---

## Data that gets better with every club

Guide prices start today with documented market values (e.g. jersey front €1,500–5,000, perimeter board €300–1,500 per season according to findasponsor) and reasoned estimates, scaled by league and spectators. During onboarding every club enters what it offers, what it gets for it and which requests turn into a yes. With enough clubs, real values replace the estimates: better price recommendations and more accurate suggestions for everyone (anonymised, only with consent).

---

## Potential

_This section is an outlook, not part of the hackathon build. Figures from third parties are linked; everything marked as an estimate is our own calculation._

### The market

| | Clubs | Source |
|---|---|---|
| Sports clubs in Germany | approx. 86,000 (29.3 m memberships) | [DOSB census 2025](https://cdn.dosb.de/user_upload/www.dosb.de/uber_uns/Bestandserhebung/Bestandserhebung_2025.pdf) |
| of which football | 23,713 | [DFB statistics 2025/26](https://www.sbfv.de/service/vereins-service/nachrichtenverband/nachrichtendetail/dfb-mitgliederstatistik-20252026) |
| Choirs (German Choir Association) | approx. 13,000 | [DCV](https://www.deutscher-chorverband.de/verband/der-verband) |
| Brass bands and orchestras (BDMV) | approx. 16,000 orchestras | [MIZ](https://miz.org/de/statistiken/mitglieder-in-den-verbaenden-des-instrumentalen-und-vokalen-amateurmusizierens) |
| Carnival clubs (BDK) | over 5,300 | [BDK](https://karnevaldeutschland.de/bundesgeschaeftsstelle/) |
| Shooting clubs (DSB, already counted in the DOSB figure) | 13,502 | [DSB](https://www.dsb.de/aktuelles/artikel/news/der-deutsche-schuetzenbund-waechst-im-vierten-jahr-in-folge) |
| **All registered associations** | **628,992** (record, March 2026) | [ZiviZ 2026](https://www.ziviz.de/publikationen/vereinssterben_oder_neue_gruendungsdynamik) |

Over 99% of sports clubs are amateur clubs (estimate: only a few hundred clubs run professional structures).

**The pain, in numbers** ([Breuer, statement to the Bundestag sports committee, 2024](https://www.bundestag.de/resource/blob/1001910/467e9d5c9a51bce41c6136f04573924f/240515-Prof-Dr-Breuer.pdf)):
- Only **25.4%** of sports clubs (approx. 22,000) have any sponsorship income at all.
- Clubs whose sponsorship fell between 2017 and 2020 lost **70%** of it on average; only few could make up for it.
- Business spending on grassroots sport sponsorship fell **17%** between 2010 and 2019.
- Sponsorship, advertising and donations together make up approx. **14%** of grassroots club income, about **€600 m** a year.

**The real bottleneck is volunteer time.** Approx. **44%** of clubs face at least one threat to their existence; the biggest one is finding and keeping volunteers, a threat to more than one club in six ([DOSB](https://www.dosb.de/aktuelles/news/detail/der-zustand-des-organisierten-sports), Sports Development Report 2023–2025). Looking for sponsors eats volunteer time, and sponsorship money buys it back: since 1 Jan 2026 clubs can pay up to **€3,300** a year tax-free per coach (Übungsleiterpauschale) and **€960** per volunteer (Ehrenamtspauschale) ([Haufe](https://www.haufe.de/personal/entgelt/steuerfreie-aufwandsentschaedigung-in-der-sozialversicherung_78_365070.html)). Three new local sponsors at about €1,100 each cover one coach's full allowance.

**Why now:** rising costs, a shrinking volunteer base, higher tax-free allowances since 2026, and AI that makes personal, sourced research affordable for every club for the first time.

### Beyond sport

About two thirds of the product (search, sources, scoring, outreach, CRM) does not depend on sport. Only the catalogue and the potential factors do. Music sponsorship works much like football sponsorship:

| Football (today's catalogue) | Music club |
|---|---|
| Perimeter board | Stage banner |
| Match programme | Concert programme |
| Match-day sponsor | "Concert presented by …" |
| Jersey | Uniform, music folders, instrument cases |
| Youth team | Youth orchestra, instrument sponsorship |

Differences: fewer events per year, an older audience with more spending power, fewer logos side by side (more attention per logo), other fitting industries (hearing care, opticians, pharmacies, tax advisers, music shops). Price ranges are similar (programme ad €80–400, concert presenting sponsor €800–3,000 per year, [motivation4teams](https://motivation4teams.de/sponsoring-fuer/kulturvereine)).

**How to extend:**
1. New field `vereinstyp` (sport, music, culture, support association, hobby …), detected by the AI during onboarding. Existing fields stay unchanged.
2. One catalogue per club type, e.g. `katalog_musik.json`.
3. A general reach factor (visitors per event × events per year, plus social media) next to today's league and spectator factors.
4. Prompts per club type: a letter to a music shop reads differently from one to a car dealer.

Order: music clubs and choirs → carnival, shooting and folk-custom clubs (large festivals, breweries and trades as classic sponsors) → school and kindergarten support associations → niche hobby clubs (small reach, so the tool recommends in-kind sponsorship and small amounts, and says so).

### End to end: from first contact to renewal

Today the product ends where the club's real work starts: after the yes.

```
TODAY:  Find → Score → Outreach → Pipeline → Yes → Take over as sponsor
                                                    │
NEXT:         ┌─────────────────────────────────────┘
              ▼
        ① Offer ─► ② Contract ─► ③ Invoice + payment ─► ④ Deliver ─► ⑤ Season report ─► ⑥ Renewal
                                                                                            │
                                                     back to ①, next season ◄──────────────┘
```

| Step | What the tool does | Builds on |
|---|---|---|
| **① Offer** | Sponsorship brochure as PDF and as a **link for the sponsor**: package, price, term, "accept offer" button | Package and price exist; brochure is on the "Next" list |
| **② Contract** | Contract from a template with package, amount and term; digital signature | Data already in `Sponsor` (`gegenleistung`, `betrag_eur`, `laufzeit_bis`) |
| **③ Invoice + payment** | Generate the invoice, collect payment via a payment provider, mark as paid, remind on open invoices | New, see below |
| **④ Deliver** | Checklist per package: board is up (photo), logo on the website, three social posts | Asset inventory |
| **⑤ Season report** | Automatic report for the sponsor: photos, matches or concerts, visitors, posts. **This is why sponsors renew.** | New |
| **⑥ Renewal** | Two months before `laufzeit_bis`: reminder plus a ready renewal offer, priced up after a promotion if it applies | Expiring-contract reminders exist |

Two effects:
- **The sponsor becomes a user.** Through the offer link and the season report, businesses join the platform without ever signing up for a marketplace. Over time we have both sides of the market.
- **The yearly subscription explains itself.** Sponsors leave, contracts expire, the board changes, new businesses open. Report and renewal give the club a reason to come back every season.

Build order: offer link and brochure → renewal → season report and delivery checklist → contract and invoice (templates checked by a lawyer) → payments last (provider, club verification and tax questions must be settled first).

### Payments through the platform

When the money flows through the platform, success becomes measurable and the treasurer is relieved of invoicing and dunning.

```
Sponsor ──pays €1,000 + service fee──► licensed platform payment provider (e.g. Stripe Connect)
                                                   │
                                     ┌─────────────┴─────────────┐
                                     ▼                           ▼
                          Club account: €1,000         Sponsorenkompass: fee
```

- **We never hold the money ourselves.** Collecting money for third parties needs a BaFin licence under the German Payment Services Supervision Act (ZAG), so payments run through a licensed platform payment provider (e.g. Stripe Connect, Mangopay, Adyen for Platforms), which also verifies the club (board, register of associations).
- **Invoice, not donation receipt.** Sponsorship comes with something in return, so a non-profit club must issue an invoice; it usually counts as a taxable business activity and is subject to VAT. Details to be confirmed with a tax adviser.
- **SEPA direct debit and bank transfer** are enough; businesses rarely pay by card.
- **The fee is charged to the sponsor** (e.g. 5% on top): the club receives the full amount, and for the business it is a deductible expense.

_Not legal advice; to be reviewed before launch._

### Business model: who pays

| Payer | What | Price (proposal, to be validated) |
|---|---|---|
| **Clubs** | One-off analysis as an entry point; season subscription with CRM, reports, renewals and a fresh analysis every season. Billed per season, because clubs budget yearly. | approx. €99 one-off, approx. €199 per season (one-off price credited towards the first season) |
| **Sponsors** | Service fee on payments made through the platform | e.g. 5% on top |
| **Federations and district sports associations** | Licence for all member clubs in a district | Annual licence by number of clubs |
| **Regional banks** (savings and cooperative banks) | "Made possible by …" licence for all clubs in their area | Annual licence, optionally exclusive per district |

**Why federations would pay:** supporting club development is one of their core tasks, but they have few advisers. The tool lets one adviser support hundreds of clubs. They get anonymised figures (potential, new sponsors, active clubs) for reports and funding applications.

**Why banks would pay:** they are among the most common grassroots sponsors, receive many requests and spread small amounts thinly. Funding the tool for all 300 clubs in a district turns that budget into help for self-help, with their name in every analysis and letter.

**Neutrality rules:** licence holders have no influence on scoring (a bank is never ranked higher because it pays), and they only see anonymised figures, never a club's candidates or contacts.

**Rough sizes (estimates):**
- Clubs: 5% of approx. 30,000 team-sports clubs × €199 ≈ **€300k per year**.
- Licences: a district of 300 clubs (list price approx. €60k) licensed for e.g. €20k per year; ten districts ≈ **€200k per year**, from ten sales conversations instead of 3,000.
- Payments: if 2% of the approx. €600 m grassroots sponsorship, advertising and donation volume flowed through the platform at a 5% fee ≈ **€600k per year** (upper bound; donations would not flow through us).
- Expansion: music, carnival, shooting and support associations, then Austria and Switzerland.

**Go-to-market order:** clubs directly first and collect success stories → one pilot district with a federation or a bank → scale. Federations and banks decide in committees, so this takes months.

---

## Architecture

```
Website URL ──► profile extraction (exa + language model) ──► club profile + inventory + existing sponsors
                                                                     │
Town ──► geocoding (Nominatim) ──► businesses nearby (Overpass/OSM)
                                                     │
                                                     ▼
                                   Pre-filter: industry, distance, gaps
                                                     │  top 15–30
                                                     ▼
                                   Research (exa.ai), with sources
                                                     │
                                                     ▼
                     Score + 3 reasons + package recommendation + outreach (language model)
                                                     │
                                                     ▼
                       Potential analysis · map · detail · pipeline · CSV export
```

Free map data provides the candidates; the paid web search only runs for the best ones after the pre-filter. All external requests are cached.

| Source | Used for | Cost |
|---|---|---|
| OpenStreetMap (Overpass API) | Businesses nearby | free |
| Nominatim | Club location to coordinates | free (max. 1 request/s, own user agent) |
| exa.ai | Club website, candidate website content, hints of sponsorship | pay per use |
| Language model | Profile extraction, scoring, package, outreach | pay per use |

### Tech stack

- **Backend:** Python, FastAPI, SQLModel, SQLite
- **Frontend:** Vite, React, TypeScript, Tailwind, react-leaflet
- **Tests:** pytest

Web search and language model each sit behind their own interface and can be swapped via configuration. Research and scoring run as background tasks with a progress indicator.

### API

FastAPI generates the API documentation automatically at `/docs`.

| Endpoint | Purpose |
|---|---|
| `POST /onboarding/analyse` | Read the website, return a profile suggestion |
| `/vereine` | Create, read, update the club profile |
| `/vereine/{id}/inventar` | Offer inventory (free / taken, price) |
| `/vereine/{id}/sponsoren` | Existing sponsors, incl. CSV import |
| `/vereine/{id}/kandidaten` | Search nearby, start research and scoring |
| `/vereine/{id}/potenzial` | Potential analysis |
| `/kandidaten/{id}/ansprache` | Letter, call script, email |
| `/vereine/{id}/export` | CSV export |

---

## Run locally

### Requirements

- Python 3.11+
- Node.js 20+
- API keys for exa.ai and a language model provider

### Configuration

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Put the keys in `backend/.env` (a `.env` in the root folder is read as well). Keys never go into the repository. With `DEMO_MODE=1` the app runs without external calls, from cached demo data.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API at http://localhost:8000, documentation at http://localhost:8000/docs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI at http://localhost:5173.

### Tests

```bash
cd backend
pytest
```

---

## Security

Analyses require an account; all club data is visible only to its own account. Implemented following OWASP ASVS and NIST SP 800-63B:

- **Passwords:** Argon2id (64 MiB, 3 iterations), at least 12 characters, no common passwords or passwords known from breaches (Have I Been Pwned, k-anonymity – only 5 characters of a hash leave the server)
- **Session:** random 256-bit token only in a `__Host-` cookie with `HttpOnly`, `Secure`, `SameSite=Strict`; only its SHA-256 is stored in the database. 7 days absolute lifetime, sign-out after 24 h of inactivity, new session on every sign-in, "sign out on all devices", a password change ends other sessions
- **Attack protection:** sign-in rate limiting (email and IP), same response and timing for unknown emails, CSRF header and origin checks, security headers (HSTS, CSP, X-Frame-Options, nosniff), cost limit for analyses per account
- **Tenant isolation:** every account is a tenant. All club data (club, sponsors, candidates, outreach, assets, assignments, activities) is tied to the account via the club; every ID in the path and in the request body is checked against the tenant, and anything foreign returns 404 (not even revealing that it exists). Two automated tests guard this: every endpoint must be protected or explicitly public, and a second tenant calls every endpoint with every method and foreign IDs without ever succeeding ([tests/test_mandanten.py](backend/tests/test_mandanten.py)). Only public data is shared (businesses from Google/OSM, sponsorship catalogue, website fetches).
- **Operations:** frontend and API on the same origin (locally via the Vite proxy `/api`), in production only over HTTPS

Still open: email confirmation and password reset (need SMTP), two-factor sign-in or passkeys, rate limiting across multiple servers (e.g. Redis).

## Legal and privacy

_Not legal advice; to be reviewed before a product launch._

- **No mass mailing from the tool.** The club decides and sends itself.
- **Letter, call or personal contact first.** Unsolicited emails can count as advertising even between businesses, so the email only comes after the first conversation.
- **Only public business data.** Contact persons only from public information (such as the imprint), stored sparingly, with source.
- **Existing sponsors** are the club's data and are used only for that club. Analyses across clubs only anonymised and with consent.

---

## Project documents

- [Build plan](docs/fahrplan.md)
- [Sponsorship catalogue](docs/sponsoring-katalog.md)
- [CSV template for existing sponsors](docs/vorlage-bestandssponsoren.csv)
- [CLAUDE.md](CLAUDE.md): working rules for the AI assistant during the build

## Team

**Timon**: treasurer of a youth support association and trainer for club managers at the South Baden Football Association (Südbadischer Fußballverband). Sponsorship comes up in every course.

## Hackathon note

Concept, research and planning were done before the hackathon, as the rules allow. All project code was written on site on 7 November 2026; the commit history shows the progress.
