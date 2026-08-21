import streamlit as st
import requests
import json
import re
from urllib.parse import quote
from statistics import median

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="AutoCheck CZ",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"

# ============================================================
# STYLE
# ============================================================

st.markdown("""
<style>

.main-title {
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 0;
}

.subtitle {
    color: #8b95a7;
    font-size: 17px;
    margin-bottom: 25px;
}

.verdict {
    padding: 25px;
    border-radius: 18px;
    margin: 20px 0;
    border: 1px solid rgba(255,255,255,.08);
}

.verdict-green {
    background: linear-gradient(135deg,#0d3327,#10251f);
}

.verdict-yellow {
    background: linear-gradient(135deg,#3b3010,#29230f);
}

.verdict-red {
    background: linear-gradient(135deg,#3b1515,#291010);
}

.verdict-title {
    font-size: 30px;
    font-weight: 800;
}

.score {
    font-size: 46px;
    font-weight: 900;
}

.metric-card {
    background: #161b26;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #252c39;
    text-align: center;
}

.metric-label {
    color: #8b95a7;
    font-size: 13px;
}

.metric-value {
    font-size: 26px;
    font-weight: 800;
}

.warning {
    background: #2d2510;
    border-left: 4px solid #eab308;
    padding: 14px;
    border-radius: 8px;
}

.good {
    background: #102b20;
    border-left: 4px solid #22c55e;
    padding: 14px;
    border-radius: 8px;
}

.bad {
    background: #321414;
    border-left: 4px solid #ef4444;
    padding: 14px;
    border-radius: 8px;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "car": {},
    "analysis": None,
    "market": [],
    "ad_text": ""
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# API
# ============================================================

def get_api_key():

    try:
        secret_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        secret_key = ""

    if secret_key:
        return secret_key

    return st.session_state.get("manual_api_key", "")


def groq_call(prompt, max_tokens=3000, temperature=0.2):

    api_key = get_api_key()

    if not api_key:
        raise ValueError(
            "Chybí Groq API klíč. Přidej GROQ_API_KEY do secrets.toml "
            "nebo ho vlož do postranního panelu."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    response = requests.post(
        GROQ_URL,
        headers=headers,
        json=payload,
        timeout=90
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Groq API chyba {response.status_code}: "
            f"{response.text[:1000]}"
        )

    data = response.json()

    return data["choices"][0]["message"]["content"].strip()


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(text):

    text = text.strip()

    # odstranění markdown ```json
    text = re.sub(
        r"^```(?:json)?",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"```$",
        "",
        text
    ).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    # pokus najít první JSON objekt
    match = re.search(
        r"\{.*\}",
        text,
        re.DOTALL
    )

    if match:

        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    raise ValueError(
        "AI nevrátila validní JSON."
    )


# ============================================================
# PARSE AD
# ============================================================

def parse_advertisement(ad_text):

    prompt = f"""
Jsi expert na extrakci údajů z českých automobilových inzerátů.

Z textu níže vytáhni pouze údaje, které jsou skutečně uvedené.
NIC SI NEVYMÝŠLEJ.

Pokud údaj není známý, použij null.

Vrať POUZE VALIDNÍ JSON.

Požadovaný formát:

{{
  "brand": "Škoda",
  "model": "Octavia",
  "generation": null,
  "year": 2021,
  "mileage_km": 118000,
  "price_czk": 389000,
  "engine": "1.5 TSI",
  "power_kw": 110,
  "fuel": "Benzín",
  "gearbox": "DSG",
  "body": "Combi",
  "drive": null,
  "owners": null,
  "service_history": null,
  "equipment": [],
  "seller_claims": [],
  "vin": null,
  "location": null,
  "condition_claims": [],
  "missing_information": []
}}

Pravidla:

- rok musí být číslo
- nájezd pouze číslo v km
- cena pouze číslo v Kč
- výkon pouze číslo
- výbavu rozděl na jednotlivé položky
- pokud prodejce tvrdí "po prvním majiteli", dej to do seller_claims
- pokud tvrdí "nehavarované", dej to do seller_claims
- pokud není jasné, zda je DSG, nepředpokládej ho
- nehádej motor pouze podle modelu
- nehádej rok
- nehádej výbavu

TEXT INZERÁTU:

{ad_text}
"""

    raw = groq_call(
        prompt,
        max_tokens=1800,
        temperature=0
    )

    return extract_json(raw)


# ============================================================
# SEARCH MARKET
# ============================================================

def search_web(query):

    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote(query)
    )

    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        if response.status_code != 200:
            return []

        html = response.text

        results = []

        # Název výsledku
        titles = re.findall(
            r'class="result__a"[^>]*>(.*?)</a>',
            html,
            re.DOTALL
        )

        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</a>',
            html,
            re.DOTALL
        )

        for i, title in enumerate(titles[:10]):

            clean_title = re.sub(
                r"<[^>]+>",
                "",
                title
            ).strip()

            snippet = ""

            if i < len(snippets):

                snippet = re.sub(
                    r"<[^>]+>",
                    "",
                    snippets[i]
                ).strip()

            results.append({
                "title": clean_title,
                "snippet": snippet
            })

        return results

    except Exception:
        return []


# ============================================================
# EXTRACT PRICES FROM SEARCH
# ============================================================

def extract_prices(results):

    prices = []

    for result in results:

        text = (
            result.get("title", "")
            + " "
            + result.get("snippet", "")
        )

        # 399 000 Kč / 399000 Kč / 399.000 Kč
        matches = re.findall(
            r"(\d{2,3}(?:[ .]\d{3})+|\d{5,6})\s*(?:Kč|CZK|,-)",
            text,
            re.IGNORECASE
        )

        for match in matches:

            number = re.sub(
                r"[ .]",
                "",
                match
            )

            try:

                value = int(number)

                if 30000 <= value <= 5000000:
                    prices.append(value)

            except ValueError:
                pass

    return prices


# ============================================================
# TECHNICAL ANALYSIS
# ============================================================

def technical_analysis(car):

    prompt = f"""
Jsi zkušený český automobilový technik a poradce pro nákup ojetých vozů.

Analyzuj následující vozidlo:

Značka: {car.get("brand")}
Model: {car.get("model")}
Generace: {car.get("generation")}
Rok: {car.get("year")}
Motor: {car.get("engine")}
Výkon: {car.get("power_kw")} kW
Palivo: {car.get("fuel")}
Převodovka: {car.get("gearbox")}
Nájezd: {car.get("mileage_km")} km
Karoserie: {car.get("body")}
Pohon: {car.get("drive")}
Výbava: {car.get("equipment")}
Tvrzení prodejce: {car.get("seller_claims")}
Servis: {car.get("service_history")}

DŮLEŽITÉ:

Nesmíš tvrdit, že konkrétní auto má závadu, pokud to z údajů nevyplývá.

Rozlišuj:

1. známý fakt
2. typické riziko dané motorizace
3. věc, kterou je nutné ověřit při prohlídce

Vrať pouze validní JSON:

{{
  "engine_reliability": 8,
  "gearbox_reliability": 8,
  "overall_technical_risk": 4,
  "known_weaknesses": [
    {{
      "title": "...",
      "risk": "Nízké/Střední/Vysoké",
      "description": "...",
      "how_to_check": "..."
    }}
  ],
  "inspection_checklist": [
    "...",
    "..."
  ],
  "expected_service_2y_czk": {{
      "low": 15000,
      "high": 50000
  }},
  "technical_summary": "..."
}}

Buď konkrétní.
"""

    raw = groq_call(
        prompt,
        max_tokens=3000,
        temperature=0.15
    )

    return extract_json(raw)


# ============================================================
# FINAL VERDICT
# ============================================================

def final_verdict(car, market_prices, technical):

    current_price = car.get("price_czk") or 0

    if market_prices:

        market_median = median(
            market_prices
        )

        low = int(
            sorted(market_prices)[
                max(0, int(len(market_prices) * 0.25))
            ]
        )

        high = int(
            sorted(market_prices)[
                min(
                    len(market_prices) - 1,
                    int(len(market_prices) * 0.75)
                )
            ]
        )

    else:

        market_median = None
        low = None
        high = None

    prompt = f"""
Jsi hlavní nákupní poradce pro ojetá auta.

Vozidlo:

{json.dumps(car, ensure_ascii=False, indent=2)}

Dostupné tržní ceny:

{market_prices}

Technická analýza:

{json.dumps(technical, ensure_ascii=False, indent=2)}

DŮLEŽITÉ:

Tržní data mohou být neúplná.
Pokud je málo skutečných cen, nesmíš tvrdit, že znáš přesnou tržní cenu.

Rozhodni:

KUPUJ
VYJEDNÁVAT
RUCE PRYČ

Vrať pouze JSON:

{{
  "verdict": "KUPUJ",
  "score": 8.2,
  "price_score": 8.5,
  "technical_score": 8,
  "risk_score": 7,
  "market_confidence": "Nízká/Střední/Vysoká",
  "fair_price_low": 350000,
  "fair_price_high": 390000,
  "recommended_max_price": 375000,
  "negotiation_target": 365000,
  "summary": "...",
  "negotiation_arguments": [
      "...",
      "..."
  ]
}}

Skóre 0–10.

Nikdy neprezentuj odhad jako jistotu.
"""

    raw = groq_call(
        prompt,
        max_tokens=1800,
        temperature=0.15
    )

    result = extract_json(raw)

    result["market_median"] = market_median
    result["market_low"] = low
    result["market_high"] = high

    return result


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("⚙️ Nastavení")

try:
    secret = st.secrets.get(
        "GROQ_API_KEY",
        ""
    )
except Exception:
    secret = ""

manual_key = st.sidebar.text_input(
    "Groq API Key",
    value=secret,
    type="password"
)

st.session_state.manual_api_key = manual_key.strip()

st.sidebar.markdown("---")

st.sidebar.caption(
    "AutoCheck je experimentální MVP. "
    "AI doporučení nenahrazuje fyzickou kontrolu vozidla."
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🚗 AutoCheck CZ</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    "Zjisti, jestli je ojetina opravdu dobrá koupě."
    "</div>",
    unsafe_allow_html=True
)


# ============================================================
# INPUT
# ============================================================

st.markdown("## 📋 1. Vlož inzerát")

ad_text = st.text_area(
    "Text inzerátu",
    height=240,
    placeholder=(
        "Zkopíruj sem celý text inzerátu z Bazoše, "
        "Sauto, TipCars apod."
    ),
    value=st.session_state.ad_text
)

st.session_state.ad_text = ad_text

if st.button(
    "✨ Automaticky načíst údaje",
    use_container_width=True
):

    if not get_api_key():

        st.error(
            "Nejdříve zadej Groq API klíč."
        )

    elif not ad_text.strip():

        st.warning(
            "Vlož text inzerátu."
        )

    else:

        with st.spinner(
            "AI analyzuje inzerát..."
        ):

            try:

                car = parse_advertisement(
                    ad_text
                )

                st.session_state.car = car

                st.success(
                    "Údaje byly načteny."
                )

            except Exception as e:

                st.error(
                    f"Chyba při načítání: {e}"
                )


# ============================================================
# CAR DATA
# ============================================================

if st.session_state.car:

    car = st.session_state.car

    st.markdown("---")
    st.markdown("## 🚘 2. Zkontroluj údaje")

    c1, c2, c3 = st.columns(3)

    with c1:

        car["brand"] = st.text_input(
            "Značka",
            value=car.get("brand") or ""
        )

        car["model"] = st.text_input(
            "Model",
            value=car.get("model") or ""
        )

        car["year"] = st.number_input(
            "Rok",
            1990,
            2026,
            value=int(
                car.get("year") or 2020
            )
        )

    with c2:

        car["mileage_km"] = st.number_input(
            "Nájezd km",
            0,
            2000000,
            value=int(
                car.get("mileage_km") or 0
            ),
            step=1000
        )

        car["price_czk"] = st.number_input(
            "Cena Kč",
            0,
            10000000,
            value=int(
                car.get("price_czk") or 0
            ),
            step=1000
        )

        car["power_kw"] = st.number_input(
            "Výkon kW",
            0,
            1000,
            value=int(
                car.get("power_kw") or 0
            )
        )

    with c3:

        car["engine"] = st.text_input(
            "Motor",
            value=car.get("engine") or ""
        )

        car["fuel"] = st.text_input(
            "Palivo",
            value=car.get("fuel") or ""
        )

        car["gearbox"] = st.text_input(
            "Převodovka",
            value=car.get("gearbox") or ""
        )

    car["body"] = st.text_input(
        "Karoserie",
        value=car.get("body") or ""
    )

    car["drive"] = st.text_input(
        "Pohon",
        value=car.get("drive") or ""
    )

    st.markdown("### 🛡️ Výbava")

    equipment_text = st.text_area(
        "Výbava",
        value=", ".join(
            car.get("equipment") or []
        ),
        height=120
    )

    car["equipment"] = [
        x.strip()
        for x in equipment_text.split(",")
        if x.strip()
    ]

    st.session_state.car = car


# ============================================================
# ANALYZE
# ============================================================

if st.session_state.car:

    st.markdown("---")

    if st.button(
        "🚀 SPUSTIT HLOUBKOVOU ANALÝZU",
        type="primary",
        use_container_width=True
    ):

        if not get_api_key():

            st.error(
                "Chybí Groq API klíč."
            )

        else:

            car = st.session_state.car

            with st.spinner(
                "Analyzuji techniku a trh..."
            ):

                try:

                    # -----------------------------
                    # MARKET SEARCH
                    # -----------------------------

                    query = (
                        f'{car.get("brand")} '
                        f'{car.get("model")} '
                        f'{car.get("year")} '
                        f'{car.get("engine")} '
                        f'cena Kč'
                    )

                    market_results = search_web(
                        query
                    )

                    market_prices = extract_prices(
                        market_results
                    )

                    # -----------------------------
                    # TECHNICAL
                    # -----------------------------

                    technical = technical_analysis(
                        car
                    )

                    # -----------------------------
                    # VERDICT
                    # -----------------------------

                    verdict = final_verdict(
                        car,
                        market_prices,
                        technical
                    )

                    st.session_state.analysis = {
                        "technical": technical,
                        "verdict": verdict,
                        "market_results": market_results
                    }

                except Exception as e:

                    st.error(
                        f"Analýza selhala: {e}"
                    )


# ============================================================
# RESULTS
# ============================================================

analysis = st.session_state.analysis

if analysis:

    technical = analysis["technical"]
    verdict = analysis["verdict"]

    st.markdown("---")
    st.markdown("## 📊 Výsledek")

    v = verdict.get(
        "verdict",
        "VYJEDNÁVAT"
    )

    score = float(
        verdict.get(
            "score",
            0
        )
    )

    if v == "KUPUJ":

        css = "verdict-green"
        emoji = "🟢"

    elif v == "RUCE PRYČ":

        css = "verdict-red"
        emoji = "🔴"

    else:

        css = "verdict-yellow"
        emoji = "🟡"

    st.markdown(
        f"""
        <div class="verdict {css}">
            <div style="display:flex;align-items:center;gap:20px">
                <div style="font-size:55px">{emoji}</div>
                <div>
                    <div style="color:#9aa5b8">
                        CELKOVÝ VERDIKT
                    </div>
                    <div class="verdict-title">
                        {v}
                    </div>
                </div>
                <div style="margin-left:auto">
                    <div class="score">
                        {score:.1f}/10
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.info(
        verdict.get(
            "summary",
            ""
        )
    )

    # ========================================================
    # METRICS
    # ========================================================

    cols = st.columns(4)

    metrics = [
        (
            "💰 Cena",
            verdict.get(
                "price_score",
                0
            )
        ),
        (
            "⚙️ Technika",
            verdict.get(
                "technical_score",
                0
            )
        ),
        (
            "⚠️ Riziko",
            verdict.get(
                "risk_score",
                0
            )
        ),
        (
            "📊 Jistota trhu",
            verdict.get(
                "market_confidence",
                "Nízká"
            )
        )
    ]

    for col, (label, value) in zip(
        cols,
        metrics
    ):

        with col:

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">
                        {label}
                    </div>
                    <div class="metric-value">
                        {value}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # ========================================================
    # PRICE
    # ========================================================

    st.markdown("## 💰 Cena")

    p1, p2, p3 = st.columns(3)

    with p1:

        st.metric(
            "Cena v inzerátu",
            f'{car.get("price_czk", 0):,} Kč'
        )

    with p2:

        st.metric(
            "Doporučená max. cena",
            f'{verdict.get("recommended_max_price", 0):,} Kč'
        )

    with p3:

        st.metric(
            "Cíl vyjednávání",
            f'{verdict.get("negotiation_target", 0):,} Kč'
        )

    st.markdown(
        f"""
        **Orientační férové rozpětí:**
        
        ### {verdict.get("fair_price_low", 0):,} – 
        {verdict.get("fair_price_high", 0):,} Kč
        """
    )

    if verdict.get(
        "market_median"
    ):

        st.caption(
            f"Z nalezených nabídek byl medián "
            f"cca {verdict['market_median']:,.0f} Kč."
        )

    else:

        st.warning(
            "Nepodařilo se získat dostatek "
            "cenových dat pro spolehlivé tržní srovnání."
        )

    # ========================================================
    # TECHNICAL
    # ========================================================

    st.markdown("---")
    st.markdown("## ⚙️ Technická analýza")

    st.write(
        technical.get(
            "technical_summary",
            ""
        )
    )

    t1, t2, t3 = st.columns(3)

    with t1:

        st.metric(
            "Spolehlivost motoru",
            f'{technical.get("engine_reliability", 0)}/10'
        )

    with t2:

        st.metric(
            "Spolehlivost převodovky",
            f'{technical.get("gearbox_reliability", 0)}/10'
        )

    with t3:

        st.metric(
            "Celkové technické riziko",
            f'{technical.get("overall_technical_risk", 0)}/10'
        )

    # ========================================================
    # WEAKNESSES
    # ========================================================

    st.markdown("### ⚠️ Typické slabiny")

    weaknesses = technical.get(
        "known_weaknesses",
        []
    )

    if weaknesses:

        for item in weaknesses:

            risk = item.get(
                "risk",
                "Střední"
            )

            st.markdown(
                f"""
                **{item.get("title", "Riziko")}**
                
                Riziko: **{risk}**
                
                {item.get("description", "")}
                
                🔎 **Jak ověřit:** 
                {item.get("how_to_check", "")}
                """
            )

            st.markdown("---")

    # ========================================================
    # SERVICE
    # ========================================================

    service = technical.get(
        "expected_service_2y_czk",
        {}
    )

    st.markdown("### 🔧 Odhad servisu na 2 roky")

    st.metric(
        "Rozpětí",
        f'{service.get("low", 0):,} – '
        f'{service.get("high", 0):,} Kč'
    )

    # ========================================================
    # CHECKLIST
    # ========================================================

    st.markdown("---")
    st.markdown("## 🔍 Checklist před koupí")

    checklist = technical.get(
        "inspection_checklist",
        []
    )

    for item in checklist:

        st.checkbox(
            item,
            key="check_" + str(
                abs(hash(item))
            )
        )

    # ========================================================
    # NEGOTIATION
    # ========================================================

    st.markdown("---")
    st.markdown("## 🤝 Nákupní taktika")

    arguments = verdict.get(
        "negotiation_arguments",
        []
    )

    for argument in arguments:

        st.markdown(
            f"- {argument}"
        )

    # ========================================================
    # MARKET SOURCES
    # ========================================================

    st.markdown("---")
    st.markdown("## 🌐 Tržní výsledky")

    market_results = analysis.get(
        "market_results",
        []
    )

    if market_results:

        for result in market_results:

            st.markdown(
                f"**{result['title']}**"
            )

            if result["snippet"]:

                st.caption(
                    result["snippet"]
                )

    else:

        st.warning(
            "Nebyla nalezena žádná tržní data."
        )

    # ========================================================
    # DISCLAIMER
    # ========================================================

    st.markdown("---")

    st.caption(
        "⚠️ AutoCheck je experimentální analytický nástroj. "
        "Technické informace a cenové odhady jsou orientační. "
        "Před koupí doporučujeme fyzickou prohlídku, "
        "diagnostiku, kontrolu VIN a ověření servisní historie."
    )
