import streamlit as st
import requests
import json
import re
from urllib.parse import quote
from statistics import median


# ============================================================
# NASTAVENÍ
# ============================================================

st.set_page_config(
    page_title="AutoCheck CZ",
    page_icon="🚗",
    layout="wide"
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Použijeme model, který podporuje JSON mode
MODEL = "openai/gpt-oss-20b"


# ============================================================
# VZHLED
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

if "car" not in st.session_state:
    st.session_state.car = {}

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "ad_text" not in st.session_state:
    st.session_state.ad_text = ""

if "debug_response" not in st.session_state:
    st.session_state.debug_response = ""


# ============================================================
# API KLÍČ
# ============================================================

def get_api_key():

    try:
        secret_key = st.secrets.get(
            "GROQ_API_KEY",
            ""
        )
    except Exception:
        secret_key = ""

    if secret_key:
        return secret_key

    return st.session_state.get(
        "manual_api_key",
        ""
    )


# ============================================================
# GROQ API
# ============================================================

def groq_call(
    prompt,
    max_tokens=3000,
    temperature=0.2,
    json_mode=False
):

    api_key = get_api_key()

    if not api_key:
        raise ValueError(
            "Chybí Groq API klíč."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Jsi přesný analytický asistent. "
                    "Pokud požaduji JSON, musí být odpověď "
                    "validní JSON bez markdownu a bez dalšího textu."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    # JSON mode
    if json_mode:
        payload["response_format"] = {
            "type": "json_object"
        }

    response = requests.post(
        GROQ_URL,
        headers=headers,
        json=payload,
        timeout=90
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"Groq API chyba {response.status_code}:\n\n"
            f"{response.text[:2000]}"
        )

    data = response.json()

    try:
        content = (
            data["choices"][0]["message"]["content"]
        )
    except Exception:

        raise RuntimeError(
            "Groq vrátil neočekávanou odpověď:\n\n"
            + json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            )[:3000]
        )

    if not content:
        raise RuntimeError(
            "Groq vrátil prázdnou odpověď."
        )

    return content.strip()


# ============================================================
# JSON PARSER
# ============================================================

def extract_json(text):

    if not text:
        raise ValueError(
            "AI vrátila prázdnou odpověď."
        )

    original_text = text

    text = text.strip()

    # Odstranění ```json
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Odstranění ```
    text = re.sub(
        r"```\s*$",
        "",
        text
    )

    text = text.strip()

    # ----------------------------------------
    # Přímý JSON
    # ----------------------------------------

    try:
        return json.loads(text)

    except Exception:
        pass

    # ----------------------------------------
    # Najdeme první {
    # ----------------------------------------

    start = text.find("{")

    if start == -1:

        raise ValueError(
            "AI nevrátila JSON objekt."
        )

    # ----------------------------------------
    # Najdeme poslední }
    # ----------------------------------------

    end = text.rfind("}")

    if end == -1:

        raise ValueError(
            "AI vrátila neúplný JSON."
        )

    candidate = text[start:end + 1]

    # ----------------------------------------
    # Pokus 1
    # ----------------------------------------

    try:

        return json.loads(candidate)

    except Exception:
        pass

    # ----------------------------------------
    # Odstranění trailing commas
    # ----------------------------------------

    candidate = re.sub(
        r",\s*([}\]])",
        r"\1",
        candidate
    )

    try:

        return json.loads(candidate)

    except Exception as e:

        raise ValueError(
            "AI nevrátila validní JSON.\n\n"
            f"Chyba parseru:\n{e}\n\n"
            f"Odpověď AI:\n{original_text[:5000]}"
        )


# ============================================================
# EXTRAKCE ÚDAJŮ Z INZERÁTU
# ============================================================

def parse_advertisement(ad_text):

    prompt = f"""
Zpracuj následující český automobilový inzerát.

Tvým úkolem je pouze vytáhnout údaje, které jsou
SKUTEČNĚ uvedené v textu.

NIC NEVYMÝŠLEJ.

Pokud údaj není uvedený, použij null.

Vrať JSON přesně v této struktuře:

{{
    "brand": null,
    "model": null,
    "generation": null,
    "year": null,
    "mileage_km": null,
    "price_czk": null,
    "engine": null,
    "power_kw": null,
    "fuel": null,
    "gearbox": null,
    "body": null,
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

PRAVIDLA:

- rok musí být celé číslo
- nájezd musí být číslo v kilometrech
- cena musí být číslo v Kč
- výkon musí být číslo v kW
- výbavu rozděl na jednotlivé položky
- tvrzení prodejce dej do seller_claims
- "nehavarované" je tvrzení prodejce, nikoliv ověřený fakt
- "1. majitel" je tvrzení prodejce
- nikdy nedoplňuj motor jen podle modelu
- nikdy nedoplňuj převodovku jen podle modelu
- nikdy nedoplňuj výbavu jen podle běžné výbavy daného modelu
- pokud údaj neznáš, dej null

NEPIŠ ŽÁDNÝ KOMENTÁŘ.

NEPIŠ MARKDOWN.

NEPIŠ ```json.

VRAŤ POUZE JSON.

TEXT INZERÁTU:

{ad_text}
"""

    raw = groq_call(
        prompt,
        max_tokens=2000,
        temperature=0,
        json_mode=True
    )

    st.session_state.debug_response = raw

    return extract_json(raw)


# ============================================================
# VYHLEDÁNÍ TRHU
# ============================================================

def search_web(query):

    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote(query)
    )

    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "Chrome/151 Safari/537.36"
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

        titles = re.findall(
            r'class="result__a"[^>]*>(.*?)</a>',
            html,
            re.DOTALL
        )

        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</',
            html,
            re.DOTALL
        )

        results = []

        for i, title in enumerate(
            titles[:10]
        ):

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

            results.append(
                {
                    "title": clean_title,
                    "snippet": snippet
                }
            )

        return results

    except Exception as e:

        return []


# ============================================================
# EXTRAKCE CEN
# ============================================================

def extract_prices(results):

    prices = []

    for result in results:

        text = (
            result.get("title", "")
            + " "
            + result.get("snippet", "")
        )

        matches = re.findall(
            r"(\d{2,3}(?:[ .]\d{3})+|\d{5,7})"
            r"\s*(?:Kč|CZK|,-)",
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

                if (
                    30000
                    <= value
                    <= 5000000
                ):

                    prices.append(value)

            except ValueError:
                pass

    return prices


# ============================================================
# TECHNICKÁ ANALÝZA
# ============================================================

def technical_analysis(car):

    prompt = f"""
Jsi zkušený český automobilový technik.

Analyzuj konkrétní vozidlo:

Značka:
{car.get("brand")}

Model:
{car.get("model")}

Generace:
{car.get("generation")}

Rok:
{car.get("year")}

Motor:
{car.get("engine")}

Výkon:
{car.get("power_kw")} kW

Palivo:
{car.get("fuel")}

Převodovka:
{car.get("gearbox")}

Nájezd:
{car.get("mileage_km")} km

Karoserie:
{car.get("body")}

Pohon:
{car.get("drive")}

Výbava:
{car.get("equipment")}

Tvrzení prodejce:
{car.get("seller_claims")}

Servisní historie:
{car.get("service_history")}

DŮLEŽITÉ:

Nesmíš tvrdit, že konkrétní auto má závadu,
pokud to z údajů nevyplývá.

Rozlišuj:

- známý fakt
- typické riziko motorizace
- co je nutné ověřit

Vrať pouze JSON:

{{
    "engine_reliability": 8,
    "gearbox_reliability": 8,
    "overall_technical_risk": 4,

    "technical_summary": "...",

    "known_weaknesses": [
        {{
            "title": "...",
            "risk": "Nízké",
            "description": "...",
            "how_to_check": "..."
        }}
    ],

    "inspection_checklist": [
        "...",
        "...",
        "..."
    ],

    "expected_service_2y_czk": {{
        "low": 15000,
        "high": 50000
    }}
}}

NEPIŠ ŽÁDNÝ KOMENTÁŘ.

VRAŤ POUZE JSON.
"""

    raw = groq_call(
        prompt,
        max_tokens=3000,
        temperature=0.1,
        json_mode=True
    )

    st.session_state.debug_response = raw

    return extract_json(raw)


# ============================================================
# FINÁLNÍ VERDIKT
# ============================================================

def final_verdict(
    car,
    market_prices,
    technical
):

    prompt = f"""
Jsi hlavní nákupní poradce pro ojetá auta.

HODNOCENÉ AUTO:

{json.dumps(
    car,
    ensure_ascii=False,
    indent=2
)}

NALEZENÉ TRŽNÍ CENY:

{json.dumps(
    market_prices,
    ensure_ascii=False
)}

TECHNICKÁ ANALÝZA:

{json.dumps(
    technical,
    ensure_ascii=False,
    indent=2
)}

DŮLEŽITÉ:

Tržní data mohou být neúplná.

Pokud je málo cen,
neprezentuj odhad jako přesnou tržní cenu.

Verdikt musí být jeden z:

"KUPUJ"

"VYJEDNÁVAT"

"RUCE PRYČ"

Vrať pouze JSON:

{{
    "verdict": "KUPUJ",

    "score": 8.2,

    "price_score": 8.5,

    "technical_score": 8.0,

    "risk_score": 7.5,

    "market_confidence": "Nízká",

    "fair_price_low": 350000,

    "fair_price_high": 390000,

    "recommended_max_price": 375000,

    "negotiation_target": 365000,

    "summary": "...",

    "negotiation_arguments": [
        "...",
        "...",
        "..."
    ]
}}

Skóre 0 až 10.

Buď konzervativní.

NEPIŠ ŽÁDNÝ KOMENTÁŘ.

VRAŤ POUZE JSON.
"""

    raw = groq_call(
        prompt,
        max_tokens=2000,
        temperature=0.1,
        json_mode=True
    )

    st.session_state.debug_response = raw

    return extract_json(raw)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("⚙️ Nastavení")

try:

    secret_key = st.secrets.get(
        "GROQ_API_KEY",
        ""
    )

except Exception:

    secret_key = ""

manual_key = st.sidebar.text_input(
    "Groq API Key",
    value=secret_key,
    type="password"
)

st.session_state.manual_api_key = (
    manual_key.strip()
)

st.sidebar.markdown("---")

st.sidebar.info(
    "AutoCheck CZ – experimentální MVP"
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">'
    '🚗 AutoCheck CZ'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Zjisti, jestli je ojetina opravdu dobrá koupě.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# INZERÁT
# ============================================================

st.markdown(
    "## 📋 1. Vlož text inzerátu"
)

ad_text = st.text_area(
    "Text inzerátu",
    height=250,
    placeholder=(
        "Zkopíruj sem celý text inzerátu "
        "z Bazoše, Sauto, TipCars apod."
    ),
    value=st.session_state.ad_text
)

st.session_state.ad_text = ad_text


if st.button(
    "✨ NAČÍST ÚDAJE Z INZERÁTU",
    use_container_width=True
):

    if not get_api_key():

        st.error(
            "❌ Chybí Groq API klíč."
        )

    elif not ad_text.strip():

        st.warning(
            "⚠️ Vlož nejdříve text inzerátu."
        )

    else:

        with st.spinner(
            "🤖 AI čte inzerát..."
        ):

            try:

                car = parse_advertisement(
                    ad_text
                )

                st.session_state.car = car

                st.success(
                    "✅ Údaje byly úspěšně načteny."
                )

            except Exception as e:

                st.error(
                    f"❌ Chyba při načítání: {e}"
                )

                # diagnostika
                if st.session_state.debug_response:

                    with st.expander(
                        "🔧 Technická diagnostika"
                    ):

                        st.code(
                            st.session_state.debug_response
                        )


# ============================================================
# ÚDAJE O AUTĚ
# ============================================================

if st.session_state.car:

    car = st.session_state.car

    st.markdown("---")

    st.markdown(
        "## 🚘 2. Zkontroluj údaje"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        car["brand"] = st.text_input(
            "Značka",
            value=car.get(
                "brand"
            ) or ""
        )

        car["model"] = st.text_input(
            "Model",
            value=car.get(
                "model"
            ) or ""
        )

        car["generation"] = st.text_input(
            "Generace",
            value=car.get(
                "generation"
            ) or ""
        )

    with c2:

        car["year"] = st.number_input(
            "Rok výroby",
            min_value=1990,
            max_value=2026,
            value=int(
                car.get(
                    "year"
                ) or 2020
            )
        )

        car["mileage_km"] = st.number_input(
            "Nájezd km",
            min_value=0,
            max_value=2000000,
            value=int(
                car.get(
                    "mileage_km"
                ) or 0
            ),
            step=1000
        )

        car["price_czk"] = st.number_input(
            "Cena Kč",
            min_value=0,
            max_value=10000000,
            value=int(
                car.get(
                    "price_czk"
                ) or 0
            ),
            step=1000
        )

    with c3:

        car["engine"] = st.text_input(
            "Motor",
            value=car.get(
                "engine"
            ) or ""
        )

        car["power_kw"] = st.number_input(
            "Výkon kW",
            min_value=0,
            max_value=1000,
            value=int(
                car.get(
                    "power_kw"
                ) or 0
            )
        )

        car["fuel"] = st.text_input(
            "Palivo",
            value=car.get(
                "fuel"
            ) or ""
        )

    c4, c5, c6 = st.columns(3)

    with c4:

        car["gearbox"] = st.text_input(
            "Převodovka",
            value=car.get(
                "gearbox"
            ) or ""
        )

    with c5:

        car["body"] = st.text_input(
            "Karoserie",
            value=car.get(
                "body"
            ) or ""
        )

    with c6:

        car["drive"] = st.text_input(
            "Pohon",
            value=car.get(
                "drive"
            ) or ""
        )

    st.markdown(
        "### 🛡️ Výbava"
    )

    equipment = car.get(
        "equipment"
    ) or []

    equipment_text = st.text_area(
        "Výbava",
        value=", ".join(
            str(x)
            for x in equipment
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
# ANALÝZA
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
                "❌ Chybí Groq API klíč."
            )

        else:

            car = st.session_state.car

            try:

                # --------------------------------------------
                # TRH
                # --------------------------------------------

                with st.spinner(
                    "🌐 Hledám srovnatelné nabídky..."
                ):

                    search_query = (
                        f"{car.get('brand')} "
                        f"{car.get('model')} "
                        f"{car.get('year')} "
                        f"{car.get('engine')} "
                        f"cena Kč"
                    )

                    market_results = search_web(
                        search_query
                    )

                    market_prices = extract_prices(
                        market_results
                    )

                # --------------------------------------------
                # TECHNIKA
                # --------------------------------------------

                with st.spinner(
                    "⚙️ Analyzuji motor, převodovku "
                    "a typické závady..."
                ):

                    technical = technical_analysis(
                        car
                    )

                # --------------------------------------------
                # VERDIKT
                # --------------------------------------------

                with st.spinner(
                    "🧠 Vytvářím finální nákupní verdikt..."
                ):

                    verdict = final_verdict(
                        car,
                        market_prices,
                        technical
                    )

                st.session_state.analysis = {
                    "technical": technical,
                    "verdict": verdict,
                    "market_results": market_results,
                    "market_prices": market_prices
                }

                st.success(
                    "✅ Analýza dokončena."
                )

            except Exception as e:

                st.error(
                    f"❌ Analýza selhala:\n\n{e}"
                )

                if st.session_state.debug_response:

                    with st.expander(
                        "🔧 Technická diagnostika"
                    ):

                        st.code(
                            st.session_state.debug_response
                        )


# ============================================================
# VÝSLEDEK
# ============================================================

if st.session_state.analysis:

    analysis = st.session_state.analysis

    technical = analysis["technical"]

    verdict = analysis["verdict"]

    car = st.session_state.car

    st.markdown("---")

    st.markdown(
        "## 📊 Výsledek analýzy"
    )

    verdict_name = verdict.get(
        "verdict",
        "VYJEDNÁVAT"
    )

    score = float(
        verdict.get(
            "score",
            0
        )
    )

    if verdict_name == "KUPUJ":

        css = "verdict-green"
        emoji = "🟢"

    elif verdict_name == "RUCE PRYČ":

        css = "verdict-red"
        emoji = "🔴"

    else:

        css = "verdict-yellow"
        emoji = "🟡"

    st.markdown(
        f"""
        <div class="verdict {css}">
            <div style="
                display:flex;
                align-items:center;
                gap:20px;
            ">
                <div style="font-size:55px">
                    {emoji}
                </div>

                <div>
                    <div style="color:#9aa5b8">
                        CELKOVÝ VERDIKT
                    </div>

                    <div class="verdict-title">
                        {verdict_name}
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
    # METRIKY
    # ========================================================

    st.markdown(
        "### 📈 Hodnocení"
    )

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
    # CENA
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 💰 Cenové hodnocení"
    )

    p1, p2, p3 = st.columns(3)

    with p1:

        st.metric(
            "Cena v inzerátu",
            f"{car.get('price_czk', 0):,} Kč"
        )

    with p2:

        st.metric(
            "Doporučená max. cena",
            f"{verdict.get('recommended_max_price', 0):,} Kč"
        )

    with p3:

        st.metric(
            "Cíl vyjednávání",
            f"{verdict.get('negotiation_target', 0):,} Kč"
        )

    st.markdown(
        f"""
        ### Férové cenové rozpětí

        ## {verdict.get('fair_price_low', 0):,} –
        {verdict.get('fair_price_high', 0):,} Kč
        """
    )

    market_prices = analysis.get(
        "market_prices",
        []
    )

    if market_prices:

        st.caption(
            "Nalezené cenové údaje: "
            + ", ".join(
                f"{x:,} Kč"
                for x in market_prices
            )
        )

    else:

        st.warning(
            "⚠️ Nepodařilo se získat dostatek "
            "tržních cen. Cenový odhad proto "
            "ber pouze orientačně."
        )

    # ========================================================
    # TECHNIKA
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## ⚙️ Technická analýza"
    )

    st.write(
        technical.get(
            "technical_summary",
            ""
        )
    )

    t1, t2, t3 = st.columns(3)

    with t1:

        st.metric(
            "Motor",
            f"{technical.get('engine_reliability', 0)}/10"
        )

    with t2:

        st.metric(
            "Převodovka",
            f"{technical.get('gearbox_reliability', 0)}/10"
        )

    with t3:

        st.metric(
            "Technické riziko",
            f"{technical.get('overall_technical_risk', 0)}/10"
        )

    # ========================================================
    # SLABINY
    # ========================================================

    st.markdown(
        "### ⚠️ Typické slabiny"
    )

    weaknesses = technical.get(
        "known_weaknesses",
        []
    )

    if weaknesses:

        for weakness in weaknesses:

            st.markdown(
                f"""
                **{weakness.get('title', 'Riziko')}**

                Riziko:
                **{weakness.get('risk', 'Střední')}**

                {weakness.get('description', '')}

                🔎 **Jak ověřit:**

                {weakness.get('how_to_check', '')}
                """
            )

            st.markdown("---")

    # ========================================================
    # SERVIS
    # ========================================================

    st.markdown(
        "### 🔧 Odhad servisu na další 2 roky"
    )

    service = technical.get(
        "expected_service_2y_czk",
        {}
    )

    st.metric(
        "Odhadované rozpětí",
        f"{service.get('low', 0):,} – "
        f"{service.get('high', 0):,} Kč"
    )

    # ========================================================
    # CHECKLIST
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 🔍 Checklist před koupí"
    )

    checklist = technical.get(
        "inspection_checklist",
        []
    )

    for i, item in enumerate(
        checklist
    ):

        st.checkbox(
            item,
            key=f"inspection_{i}"
        )

    # ========================================================
    # VYJEDNÁVÁNÍ
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 🤝 Jak vyjednávat"
    )

    arguments = verdict.get(
        "negotiation_arguments",
        []
    )

    for argument in arguments:

        st.markdown(
            f"- {argument}"
        )

    # ========================================================
    # TRŽNÍ VÝSLEDKY
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 🌐 Nalezené tržní výsledky"
    )

    market_results = analysis.get(
        "market_results",
        []
    )

    if market_results:

        for result in market_results:

            st.markdown(
                f"**{result.get('title', '')}**"
            )

            if result.get(
                "snippet"
            ):

                st.caption(
                    result["snippet"]
                )

    else:

        st.info(
            "Žádné výsledky nebyly nalezeny."
        )


# ============================================================
# DEBUG
# ============================================================

if st.session_state.debug_response:

    with st.expander(
        "🔧 Poslední odpověď AI – diagnostika"
    ):

        st.code(
            st.session_state.debug_response
        )


# ============================================================
# PATIČKA
# ============================================================

st.markdown("---")

st.caption(
    "⚠️ AutoCheck CZ je experimentální MVP. "
    "Výsledky AI a cenové odhady jsou orientační. "
    "Před koupí doporučujeme fyzickou kontrolu vozidla, "
    "diagnostiku, kontrolu VIN a ověření servisní historie."
)
