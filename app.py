import streamlit as st
from google import genai
from google.genai import types
import json
import re


# ============================================================
# AUTOCHECK CZ
# ============================================================

st.set_page_config(
    page_title="AutoCheck CZ",
    page_icon="🚗",
    layout="wide"
)

# Model necháváme na jednom místě,
# abychom ho později mohli jednoduše změnit.
MODEL = "gemini-3.7-flash"


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

.metric-card {
    padding: 18px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,.10);
    background: rgba(255,255,255,.035);
    margin-bottom: 12px;
}

.metric-label {
    color: #8b95a7;
    font-size: 13px;
    margin-bottom: 5px;
}

.metric-value {
    font-size: 22px;
    font-weight: 700;
}

.verdict-box {
    padding: 28px;
    border-radius: 18px;
    margin: 20px 0 30px 0;
    border: 1px solid rgba(255,255,255,.12);
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
    font-size: 34px;
    font-weight: 900;
}

.score {
    font-size: 48px;
    font-weight: 900;
    margin-top: 8px;
}

.risk-card {
    padding: 16px;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,.10);
    margin-bottom: 10px;
}

.price-good {
    font-size: 30px;
    font-weight: 800;
}

.small-muted {
    color: #8b95a7;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# API KEY
# ============================================================

def get_api_key():

    try:
        key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        raise Exception(
            "Chybí GEMINI_API_KEY ve Streamlit Secrets.\n\n"
            "V Streamlit Cloud otevři:\n"
            "Settings → Secrets\n\n"
            'a nastav:\n'
            'GEMINI_API_KEY = "tvůj_klíč"'
        )

    if not key:
        raise Exception(
            "GEMINI_API_KEY ve Streamlit Secrets je prázdný."
        )

    return key.strip()


# ============================================================
# JSON SCHEMA
# ============================================================

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {

        "verdict": {
            "type": "string",
            "enum": [
                "KUPUJ",
                "VYJEDNÁVAT",
                "RUCE PRYČ"
            ]
        },

        "score": {
            "type": "integer"
        },

        "summary": {
            "type": "string"
        },

        "car": {
            "type": "object",
            "properties": {
                "brand": {"type": "string"},
                "model": {"type": "string"},
                "year": {"type": "string"},
                "engine": {"type": "string"},
                "power": {"type": "string"},
                "fuel": {"type": "string"},
                "gearbox": {"type": "string"},
                "drive": {"type": "string"},
                "body": {"type": "string"},
                "mileage": {"type": "string"},
                "price": {"type": "string"}
            },
            "required": [
                "brand",
                "model",
                "year",
                "engine",
                "power",
                "fuel",
                "gearbox",
                "drive",
                "body",
                "mileage",
                "price"
            ]
        },

        "equipment": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "price_analysis": {
            "type": "object",
            "properties": {
                "fair_price": {"type": "string"},
                "good_buy_price": {"type": "string"},
                "max_price": {"type": "string"},
                "explanation": {"type": "string"}
            },
            "required": [
                "fair_price",
                "good_buy_price",
                "max_price",
                "explanation"
            ]
        },

        "technical": {
            "type": "object",
            "properties": {
                "engine": {"type": "string"},
                "gearbox": {"type": "string"},
                "reliability": {"type": "string"},
                "important_points": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "engine",
                "gearbox",
                "reliability",
                "important_points"
            ]
        },

        "risks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "risk": {"type": "string"},
                    "symptoms": {"type": "string"},
                    "verification": {"type": "string"},
                    "repair_cost": {"type": "string"}
                },
                "required": [
                    "risk",
                    "symptoms",
                    "verification",
                    "repair_cost"
                ]
            }
        },

        "checklist": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "why": {"type": "string"}
                },
                "required": [
                    "item",
                    "why"
                ]
            }
        },

        "service": {
            "type": "object",
            "properties": {
                "normal": {"type": "string"},
                "likely_repairs": {"type": "string"},
                "worst_case": {"type": "string"},
                "two_year_total": {"type": "string"}
            },
            "required": [
                "normal",
                "likely_repairs",
                "worst_case",
                "two_year_total"
            ]
        },

        "negotiation": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "conclusion": {
            "type": "string"
        }

    },

    "required": [
        "verdict",
        "score",
        "summary",
        "car",
        "equipment",
        "price_analysis",
        "technical",
        "risks",
        "checklist",
        "service",
        "negotiation",
        "conclusion"
    ]
}


# ============================================================
# GEMINI
# ============================================================

def analyze_with_gemini(ad_text):

    api_key = get_api_key()

    client = genai.Client(
        api_key=api_key
    )

    prompt = f"""
Jsi seniorní český expert na ojeté automobily.

Analyzuj KONKRÉTNÍ AUTOMOBIL z následujícího inzerátu.

==================================================
INZERÁT
==================================================

{ad_text}

==================================================
HLAVNÍ CÍL
==================================================

Kupující chce vědět:

1. Je to dobrá koupě?
2. Je cena přiměřená?
3. Jaká jsou největší technická rizika?
4. Co musí zkontrolovat?
5. Kolik může stát servis?
6. Kolik maximálně zaplatit?

==================================================
DŮLEŽITÁ PRAVIDLA
==================================================

NIKDY si nevymýšlej údaje o konkrétním autě.

Pokud údaj v inzerátu není:
"neuvedeno"

Rozlišuj:

- skutečný údaj z inzerátu
- typický problém daného modelu
- věc, kterou je nutné ověřit

Pokud neznáš přesnou cenu konkrétního auta na trhu,
nepředstírej přesnost.

U ceny používej rozumný odhad založený na:
- modelu
- roku
- motoru
- převodovce
- nájezdu
- výbavě
- stavu
- obecné znalosti trhu

Pokud je informace nejistá,
uveď tuto nejistotu.

==================================================
VERDIKT
==================================================

KUPUJ:
Auto je za zajímavou cenu a nevidíš zásadní riziko.

VYJEDNÁVAT:
Auto může být dobré, ale cena nebo rizika vyžadují jednání.

RUCE PRYČ:
Cena, stav nebo rizika jsou natolik špatné,
že bys hledal jiné auto.

Skóre:
1 = velmi špatná koupě
10 = mimořádně dobrá koupě

==================================================
TECHNICKÁ ANALÝZA
==================================================

Buď konkrétní pro daný motor a převodovku.

Zajímají mě například:

- rozvody
- turbo
- vstřikování
- olejová spotřeba
- chlazení
- DPF
- EGR
- AdBlue
- dvouhmota
- spojka
- DSG
- automatická převodovka
- podvozek
- elektronika

Použij pouze relevantní položky.

==================================================
RIZIKA
==================================================

Uveď nejvýše 8 nejdůležitějších rizik.

U každého napiš:

- co je riziko
- jak se projeví
- jak ho ověřit
- orientační cenu opravy

Nepiš obecné nesmysly.
Rizika musí být relevantní pro konkrétní auto.

==================================================
CHECKLIST
==================================================

Vytvoř 10 konkrétních bodů pro prohlídku.

Přizpůsob je konkrétnímu autu.

==================================================
SERVIS
==================================================

Odhadni:

běžný servis:
pravděpodobné opravy:
špatný scénář:
celkem za 2 roky:

Částky uváděj v Kč.

==================================================
VYJEDNÁVÁNÍ
==================================================

Vymysli konkrétní argumenty,
kterými může kupující srazit cenu.

==================================================
DŮLEŽITÉ
==================================================

Výstup musí být validní JSON podle přiloženého schématu.

Nepřidávej žádný text mimo JSON.
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.15,
            max_output_tokens=6000,
            response_mime_type="application/json",
            response_schema=ANALYSIS_SCHEMA
        )
    )

    if not response.text:
        raise Exception(
            "Gemini vrátil prázdnou odpověď."
        )

    try:

        return json.loads(
            response.text
        )

    except json.JSONDecodeError as e:

        raise Exception(
            "Gemini vrátil neplatný JSON:\n\n"
            + response.text[:5000]
            + f"\n\nJSON chyba: {e}"
        )


# ============================================================
# KARTIČKA
# ============================================================

def metric(label, value):

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


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "⚙️ AutoCheck CZ"
)

st.sidebar.success(
    "🔐 Gemini API ze Secrets"
)

st.sidebar.markdown("---")

st.sidebar.write(
    "Model:"
)

st.sidebar.code(
    MODEL
)

st.sidebar.markdown("---")

st.sidebar.caption(
    "Strukturovaný AI výstup"
)

st.sidebar.caption(
    "1 API request / analýza"
)


# ============================================================
# NADPIS
# ============================================================

st.markdown(
    '<div class="main-title">🚗 AutoCheck CZ</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Expertní nákupní analýza ojetého automobilu'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# INZERÁT
# ============================================================

st.markdown(
    "## 📋 Inzerát"
)

ad_text = st.text_area(
    "Vlož celý text inzerátu",
    height=380,
    placeholder=(
        "Zkopíruj sem celý text z Bazoše, "
        "Sauto, TipCars, Mobile.de apod."
    )
)


# ============================================================
# TLAČÍTKO
# ============================================================

if st.button(
    "🚀 ANALYZOVAT AUTO",
    type="primary",
    use_container_width=True
):

    if not ad_text.strip():

        st.warning(
            "Nejdříve vlož text inzerátu."
        )

    else:

        with st.spinner(
            "🔎 Gemini analyzuje automobil..."
        ):

            try:

                result = analyze_with_gemini(
                    ad_text
                )

                st.session_state[
                    "car_analysis"
                ] = result

            except Exception as e:

                st.error(
                    str(e)
                )


# ============================================================
# VÝSLEDEK
# ============================================================

if "car_analysis" in st.session_state:

    data = st.session_state[
        "car_analysis"
    ]

    # ========================================================
    # VERDIKT
    # ========================================================

    verdict = data.get(
        "verdict",
        "VYJEDNÁVAT"
    )

    score = data.get(
        "score",
        "?"
    )

    summary = data.get(
        "summary",
        ""
    )


    if verdict == "KUPUJ":

        css = "verdict-green"
        emoji = "🟢"

    elif verdict == "VYJEDNÁVAT":

        css = "verdict-yellow"
        emoji = "🟡"

    else:

        css = "verdict-red"
        emoji = "🔴"


    st.markdown(
        f"""
        <div class="verdict-box {css}">

            <div class="small-muted">
                NÁKUPNÍ VERDIKT
            </div>

            <div class="verdict-title">
                {emoji} {verdict}
            </div>

            <div class="score">
                {score}/10
            </div>

            <div style="
                font-size:17px;
                margin-top:12px;
            ">
                {summary}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # AUTO
    # ========================================================

    st.markdown(
        "## 🚘 Identifikace auta"
    )

    car = data.get(
        "car",
        {}
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        metric(
            "Model",
            f"{car.get('brand','')} "
            f"{car.get('model','')}"
        )

        metric(
            "Motor",
            car.get(
                "engine",
                "neuvedeno"
            )
        )

        metric(
            "Palivo",
            car.get(
                "fuel",
                "neuvedeno"
            )
        )

    with c2:

        metric(
            "Rok",
            car.get(
                "year",
                "neuvedeno"
            )
        )

        metric(
            "Převodovka",
            car.get(
                "gearbox",
                "neuvedeno"
            )
        )

        metric(
            "Nájezd",
            car.get(
                "mileage",
                "neuvedeno"
            )
        )

    with c3:

        metric(
            "Cena",
            car.get(
                "price",
                "neuvedeno"
            )
        )

        metric(
            "Výkon",
            car.get(
                "power",
                "neuvedeno"
            )
        )

        metric(
            "Pohon",
            car.get(
                "drive",
                "neuvedeno"
            )
        )


    # ========================================================
    # CENA
    # ========================================================

    st.markdown(
        "## 💰 Cena"
    )

    price = data.get(
        "price_analysis",
        {}
    )

    p1, p2, p3 = st.columns(3)

    with p1:

        metric(
            "Férová cena",
            price.get(
                "fair_price",
                "neuvedeno"
            )
        )

    with p2:

        metric(
            "Dobrá nákupní cena",
            price.get(
                "good_buy_price",
                "neuvedeno"
            )
        )

    with p3:

        metric(
            "Maximum",
            price.get(
                "max_price",
                "neuvedeno"
            )
        )

    st.info(
        price.get(
            "explanation",
            ""
        )
    )


    # ========================================================
    # VÝBAVA
    # ========================================================

    st.markdown(
        "## 🛡️ Výbava"
    )

    equipment = data.get(
        "equipment",
        []
    )

    if equipment:

        cols = st.columns(2)

        for i, item in enumerate(
            equipment
        ):

            with cols[i % 2]:

                st.markdown(
                    f"✓ {item}"
                )

    else:

        st.write(
            "Výbava neuvedena."
        )


    # ========================================================
    # TECHNIKA
    # ========================================================

    st.markdown(
        "## ⚙️ Technika"
    )

    technical = data.get(
        "technical",
        {}
    )

    st.markdown(
        "### Motor"
    )

    st.write(
        technical.get(
            "engine",
            ""
        )
    )

    st.markdown(
        "### Převodovka"
    )

    st.write(
        technical.get(
            "gearbox",
            ""
        )
    )

    st.markdown(
        "### Spolehlivost"
    )

    st.write(
        technical.get(
            "reliability",
            ""
        )
    )

    st.markdown(
        "### Co ověřit"
    )

    for item in technical.get(
        "important_points",
        []
    ):

        st.markdown(
            f"• {item}"
        )


    # ========================================================
    # RIZIKA
    # ========================================================

    st.markdown(
        "## ⚠️ Největší rizika"
    )

    risks = data.get(
        "risks",
        []
    )

    for i, risk in enumerate(
        risks,
        start=1
    ):

        with st.expander(
            f"{i}. {risk.get('risk','Riziko')}"
        ):

            st.markdown(
                "**Jak se projevuje:**"
            )

            st.write(
                risk.get(
                    "symptoms",
                    ""
                )
            )

            st.markdown(
                "**Jak ověřit:**"
            )

            st.write(
                risk.get(
                    "verification",
                    ""
                )
            )

            st.markdown(
                "**Orientační oprava:**"
            )

            st.write(
                risk.get(
                    "repair_cost",
                    ""
                )
            )


    # ========================================================
    # CHECKLIST
    # ========================================================

    st.markdown(
        "## 🔍 Checklist prohlídky"
    )

    checklist = data.get(
        "checklist",
        []
    )

    for i, item in enumerate(
        checklist,
        start=1
    ):

        st.markdown(
            f"### {i}. {item.get('item','')}"
        )

        st.write(
            item.get(
                "why",
                ""
            )
        )


    # ========================================================
    # SERVIS
    # ========================================================

    st.markdown(
        "## 🔧 Servis na 2 roky"
    )

    service = data.get(
        "service",
        {}
    )

    s1, s2, s3, s4 = st.columns(4)

    with s1:

        metric(
            "Běžný servis",
            service.get(
                "normal",
                "neuvedeno"
            )
        )

    with s2:

        metric(
            "Pravděpodobné opravy",
            service.get(
                "likely_repairs",
                "neuvedeno"
            )
        )

    with s3:

        metric(
            "Špatný scénář",
            service.get(
                "worst_case",
                "neuvedeno"
            )
        )

    with s4:

        metric(
            "Celkem 2 roky",
            service.get(
                "two_year_total",
                "neuvedeno"
            )
        )


    # ========================================================
    # VYJEDNÁVÁNÍ
    # ========================================================

    st.markdown(
        "## 🤝 Jak vyjednávat"
    )

    negotiation = data.get(
        "negotiation",
        []
    )

    for item in negotiation:

        st.markdown(
            f"• {item}"
        )


    # ========================================================
    # ZÁVĚR
    # ========================================================

    st.markdown(
        "## 🏁 Závěr"
    )

    st.info(
        data.get(
            "conclusion",
            ""
        )
    )


# ============================================================
# PATIČKA
# ============================================================

st.markdown("---")

st.caption(
    "AutoCheck CZ – MVP. "
    "AI analýza nenahrazuje fyzickou kontrolu, "
    "diagnostiku ani ověření VIN."
)
