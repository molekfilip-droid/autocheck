import streamlit as st
from google import genai
from google.genai import types
import json
import time


# ============================================================
# AUTO CHECK CZ
# ============================================================

st.set_page_config(
    page_title="AutoCheck CZ",
    page_icon="🚗",
    layout="wide"
)

MODEL = "gemini-3.6-flash"


# ============================================================
# VZHLED
# ============================================================

st.markdown("""
<style>

.block-container {
    max-width: 1400px;
    padding-top: 2rem;
}

.big-title {
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 0;
}

.subtitle {
    color: #9aa5b8;
    font-size: 17px;
    margin-bottom: 30px;
}

/* INFO KARTY */

.info-box {
    padding: 18px;
    border-radius: 12px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 12px;
}

.info-label {
    color: #9aa5b8;
    font-size: 13px;
}

.info-value {
    font-size: 20px;
    font-weight: 700;
    margin-top: 4px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# API KEY
# ============================================================

def get_api_key():

    try:
        api_key = st.secrets["GEMINI_API_KEY"]

    except Exception:

        raise Exception(
            "❌ Chybí GEMINI_API_KEY ve Streamlit Secrets.\n\n"
            "Streamlit Cloud → Settings → Secrets\n\n"
            'GEMINI_API_KEY = "tvůj_api_klíč"'
        )

    if not api_key:
        raise Exception(
            "❌ GEMINI_API_KEY je prázdný."
        )

    return api_key.strip()


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
# GEMINI ANALÝZA
# ============================================================

def analyze_car(ad_text):

    api_key = get_api_key()

    client = genai.Client(
        api_key=api_key
    )

    prompt = f"""
Jsi seniorní český expert na ojeté automobily.

Analyzuj KONKRÉTNÍ automobil podle tohoto inzerátu:

==================================================
INZERÁT
==================================================

{ad_text}

==================================================
CÍL ANALÝZY
==================================================

Kupující chce zjistit:

1. Zda je auto dobrá koupě.
2. Zda odpovídá cena.
3. Jaká jsou technická rizika.
4. Co musí při prohlídce zkontrolovat.
5. Kolik může stát servis.
6. Jaká je maximální rozumná nákupní cena.
7. Jakými argumenty lze vyjednávat.

==================================================
DŮLEŽITÁ PRAVIDLA
==================================================

NEVYMÝŠLEJ si údaje o konkrétním vozidle.

Pokud údaj není v inzerátu znám:

"neuvedeno"

Rozlišuj mezi:

- údajem přímo uvedeným v inzerátu
- typickou vlastností/problémem daného modelu
- věcí, kterou je nutné před koupí ověřit

Pokud si nejsi jistý, přiznej nejistotu.

Buď konkrétní.

Nepoužívej obecné rady typu:

"Nechte auto zkontrolovat."

Místo toho napiš přesně CO kontrolovat a PROČ.

==================================================
VERDIKT
==================================================

KUPUJ:

Auto je za danou cenu velmi zajímavé
a rizika jsou přijatelná.

VYJEDNÁVAT:

Auto může být dobrá koupě,
ale cena nebo některá rizika vyžadují vyjednávání
nebo kontrolu před koupí.

RUCE PRYČ:

Auto je výrazně předražené,
má zásadní riziko nebo je celkově špatná koupě.

Skóre:

1 = velmi špatná koupě

10 = mimořádně dobrá koupě

==================================================
CENA
==================================================

Odhadni:

- férovou cenu
- dobrou nákupní cenu
- maximální cenu, kterou bys osobně zaplatil

Zohledni:

- rok
- nájezd
- motor
- převodovku
- výkon
- výbavu
- karoserii
- pohon
- stav
- cenu uvedenou v inzerátu

Nedávej falešnou přesnost.

==================================================
MOTOR A PŘEVODOVKA
==================================================

Analyzuj konkrétní motorizaci a převodovku.

Zaměř se pouze na relevantní věci:

- rozvody
- turbo
- vstřikování
- spotřebu oleje
- chlazení
- DPF
- EGR
- AdBlue
- dvouhmotu
- spojku
- DSG
- automatickou převodovku
- podvozek
- elektroniku

==================================================
RIZIKA
==================================================

Uveď maximálně 8 nejdůležitějších rizik.

U každého:

1. Co je problém.
2. Jak se projevuje.
3. Jak ho ověřit.
4. Kolik může stát oprava.

==================================================
CHECKLIST
==================================================

Vytvoř 10 konkrétních bodů kontroly.

Checklist musí být použitelný přímo při návštěvě auta.

==================================================
SERVIS
==================================================

Odhadni:

- běžný servis
- pravděpodobné opravy
- špatný scénář
- celkové náklady na 2 roky

Vše uváděj v Kč.

==================================================
VYJEDNÁVÁNÍ
==================================================

Napiš konkrétní argumenty,
které může kupující použít proti prodejci.

Pokud například chybí doložený servis,
uveď jaký servis chybí a přibližnou hodnotu.

==================================================
ZÁVĚR
==================================================

Jednoznačně napiš:

- koupil bych / nekoupil bych
- za jakou cenu
- proč

==================================================
VÝSTUP
==================================================

Vrať POUZE validní JSON podle přiloženého schématu.

Žádný Markdown.

Žádný HTML.

Žádný text před JSON.

Žádný text za JSON.
"""

    try:

        response = client.models.generate_content(

            model=MODEL,

            contents=prompt,

            config=types.GenerateContentConfig(

                response_mime_type="application/json",

                response_schema=ANALYSIS_SCHEMA,

                max_output_tokens=6000
            )
        )

    except Exception as e:

        error_text = str(e)

        if (
            "503" in error_text
            or
            "UNAVAILABLE" in error_text
            or
            "high demand" in error_text.lower()
        ):

            st.warning(
                "Gemini je momentálně přetížený. "
                "Zkouším druhý pokus..."
            )

            time.sleep(8)

            try:

                response = client.models.generate_content(

                    model=MODEL,

                    contents=prompt,

                    config=types.GenerateContentConfig(

                        response_mime_type="application/json",

                        response_schema=ANALYSIS_SCHEMA,

                        max_output_tokens=6000
                    )
                )

            except Exception as e2:

                raise Exception(
                    "Gemini je momentálně nedostupný.\n\n"
                    f"První pokus:\n{error_text}\n\n"
                    f"Druhý pokus:\n{e2}"
                )

        else:

            raise e


    if not response.text:

        raise Exception(
            "Gemini vrátil prázdnou odpověď."
        )


    try:

        return json.loads(
            response.text
        )

    except Exception:

        raise Exception(
            "Gemini vrátil neplatný JSON:\n\n"
            + response.text[:5000]
        )


# ============================================================
# INFO KARTA
# ============================================================

def metric(label, value):

    if value is None:
        value = "neuvedeno"

    st.markdown(
        f"""
        <div class="info-box">
            <div class="info-label">
                {label}
            </div>

            <div class="info-value">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# HLAVIČKA
# ============================================================

st.markdown(
    '<div class="big-title">🚗 AutoCheck CZ</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Expertní analýza ojetého automobilu'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "⚙️ AutoCheck CZ"
)

st.sidebar.success(
    "Gemini API aktivní"
)

st.sidebar.markdown("---")

st.sidebar.write(
    "Použitý model:"
)

st.sidebar.code(
    MODEL
)

st.sidebar.markdown("---")

st.sidebar.caption(
    "AI analýza ojetých automobilů"
)


# ============================================================
# TEXT INZERÁTU
# ============================================================

st.markdown(
    "## 📋 Vlož text inzerátu"
)

ad_text = st.text_area(
    "Celý text inzerátu",
    height=400,

    placeholder=(
        "Zkopíruj sem celý text inzerátu "
        "z Bazoše, Sauto, TipCars, Mobile.de..."
    )
)


# ============================================================
# SPUŠTĚNÍ ANALÝZY
# ============================================================

if st.button(
    "🚀 SPUSTIT ANALÝZU",
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

                result = analyze_car(
                    ad_text
                )

                st.session_state[
                    "analysis"
                ] = result

            except Exception as e:

                st.error(
                    str(e)
                )


# ============================================================
# VÝSLEDEK
# ============================================================

if "analysis" in st.session_state:

    data = st.session_state[
        "analysis"
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


    st.markdown(
        "## 🏁 NÁKUPNÍ VERDIKT"
    )


    if verdict == "KUPUJ":

        st.success(
            f"🟢 **KUPUJ — {score}/10**"
        )

    elif verdict == "VYJEDNÁVAT":

        st.warning(
            f"🟡 **VYJEDNÁVAT — {score}/10**"
        )

    else:

        st.error(
            f"🔴 **RUCE PRYČ — {score}/10**"
        )


    st.markdown(
        "### Shrnutí"
    )

    st.write(
        summary
    )


    # ========================================================
    # IDENTIFIKACE
    # ========================================================

    st.markdown(
        "## 🚘 Identifikace vozidla"
    )

    car = data.get(
        "car",
        {}
    )


    c1, c2, c3 = st.columns(3)


    with c1:

        metric(
            "Model",
            (
                car.get("brand", "")
                + " "
                + car.get("model", "")
            ).strip()
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
        "## 💰 Hodnocení ceny"
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
            "Maximální cena",
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

        col1, col2 = st.columns(2)

        for i, item in enumerate(
            equipment
        ):

            with (
                col1
                if i % 2 == 0
                else col2
            ):

                st.markdown(
                    f"✓ {item}"
                )

    else:

        st.write(
            "Výbava nebyla uvedena."
        )


    # ========================================================
    # TECHNICKÁ ANALÝZA
    # ========================================================

    st.markdown(
        "## ⚙️ Technická analýza"
    )

    technical = data.get(
        "technical",
        {}
    )


    st.markdown(
        "### 🔧 Motor"
    )

    st.write(
        technical.get(
            "engine",
            ""
        )
    )


    st.markdown(
        "### ⚙️ Převodovka"
    )

    st.write(
        technical.get(
            "gearbox",
            ""
        )
    )


    st.markdown(
        "### 🛡️ Spolehlivost"
    )

    st.write(
        technical.get(
            "reliability",
            ""
        )
    )


    st.markdown(
        "### 🔎 Co ověřit"
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
            f"{i}. {risk.get('risk', 'Riziko')}"
        ):

            st.markdown(
                "**Jak se projevuje**"
            )

            st.write(
                risk.get(
                    "symptoms",
                    ""
                )
            )


            st.markdown(
                "**Jak ověřit**"
            )

            st.write(
                risk.get(
                    "verification",
                    ""
                )
            )


            st.markdown(
                "**Cena opravy**"
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
        "## 🔍 Checklist při prohlídce"
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
            f"### {i}. {item.get('item', '')}"
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
        "## 🔧 Odhad servisu na 2 roky"
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
        "## 🤝 Jak vyjednávat cenu"
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
    # KONEČNÝ ZÁVĚR
    # ========================================================

    st.markdown(
        "## 🏁 Konečné doporučení"
    )

    st.info(
        data.get(
            "conclusion",
            ""
        )
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "AutoCheck CZ MVP • "
    "AI analýza nenahrazuje fyzickou kontrolu, "
    "diagnostiku ani ověření VIN."
)
