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

.verdict {
    padding: 28px;
    border-radius: 18px;
    margin: 20px 0 30px 0;
    border: 1px solid rgba(255,255,255,.12);
}

.green {
    background: linear-gradient(135deg,#0b3024,#10231d);
}

.yellow {
    background: linear-gradient(135deg,#3a3010,#29230f);
}

.red {
    background: linear-gradient(135deg,#391414,#281010);
}

.verdict-small {
    color: #9aa5b8;
    font-size: 14px;
}

.verdict-title {
    font-size: 34px;
    font-weight: 900;
}

.score {
    font-size: 48px;
    font-weight: 900;
}

.card {
    padding: 18px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,.10);
    background: rgba(255,255,255,.035);
    margin-bottom: 12px;
}

.card-label {
    color: #8b95a7;
    font-size: 13px;
}

.card-value {
    font-size: 21px;
    font-weight: 700;
    margin-top: 4px;
}

.risk {
    padding: 16px;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,.10);
    margin-bottom: 10px;
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
# GEMINI REQUEST S RETRY
# ============================================================

def generate_with_retry(client, prompt):

    max_attempts = 4

    delays = [
        5,
        10,
        20
    ]

    last_error = None

    for attempt in range(max_attempts):

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

            return response

        except Exception as e:

            last_error = e

            error_text = str(e)

            is_503 = (
                "503" in error_text
                or
                "UNAVAILABLE" in error_text
                or
                "high demand" in error_text.lower()
                or
                "service unavailable" in error_text.lower()
            )

            if not is_503:

                raise e

            if attempt < max_attempts - 1:

                wait_time = delays[attempt]

                st.warning(
                    f"Gemini je momentálně přetížený. "
                    f"Automatický pokus "
                    f"{attempt + 2}/{max_attempts} "
                    f"za {wait_time} sekund..."
                )

                time.sleep(
                    wait_time
                )

    raise Exception(
        "Gemini je momentálně nedostupný "
        "po několika automatických pokusech.\n\n"
        f"Poslední chyba:\n{last_error}"
    )


# ============================================================
# ANALÝZA
# ============================================================

def analyze_car(ad_text):

    api_key = get_api_key()

    client = genai.Client(
        api_key=api_key
    )

    prompt = f"""
Jsi seniorní český odborník na ojetá auta.

Analyzuj konkrétní automobil z tohoto inzerátu:

========================
INZERÁT
========================

{ad_text}

========================
CÍL
========================

Kupující chce zjistit:

- zda je auto dobrá koupě
- zda odpovídá cena
- jaká jsou technická rizika
- co musí při prohlídce ověřit
- kolik může stát servis
- kolik maximálně zaplatit

========================
PRAVIDLA
========================

Nevymýšlej si údaje.

Pokud údaj není v inzerátu:

"neuvedeno"

Rozlišuj mezi:

1. informací z inzerátu
2. typickou vlastností modelu
3. věcí, kterou je nutné ověřit

Pokud si nejsi jistý, napiš to.

========================
VERDIKT
========================

KUPUJ:
Velmi zajímavá nabídka.

VYJEDNÁVAT:
Auto může být dobré, ale cena nebo rizika vyžadují jednání.

RUCE PRYČ:
Nabídka je příliš riziková, předražená nebo má zásadní problém.

Skóre:

1 = velmi špatná koupě

10 = mimořádně dobrá koupě

========================
CENA
========================

Odhaduj férovou cenu podle:

- modelu
- roku
- motoru
- převodovky
- nájezdu
- výbavy
- obecné znalosti trhu

Nedávej falešnou přesnost.

========================
TECHNIKA
========================

Zaměř se na konkrétní motor a převodovku.

Relevantní mohou být:

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
- automat
- podvozek
- elektronika

Používej pouze relevantní položky.

========================
RIZIKA
========================

Maximálně 8 nejdůležitějších.

U každého:

- riziko
- projevy
- jak ověřit
- cena opravy

========================
CHECKLIST
========================

10 konkrétních bodů.

Přizpůsob konkrétnímu autu.

========================
SERVIS
========================

Odhad:

- běžný servis
- pravděpodobné opravy
- špatný scénář
- celkem za 2 roky

Částky v Kč.

========================
VYJEDNÁVÁNÍ
========================

Napiš konkrétní argumenty,
kterými lze cenu snížit.

========================
DŮLEŽITÉ
========================

Vrať pouze validní JSON podle schématu.

Žádný Markdown.

Žádný text před JSON.

Žádný text za JSON.
"""

    response = generate_with_retry(
        client,
        prompt
    )

    if not response.text:

        raise Exception(
            "Gemini vrátil prázdnou odpověď."
        )

    try:

        return json.loads(
            response.text
        )

    except Exception as e:

        raise Exception(
            "Gemini vrátil neplatný JSON.\n\n"
            + response.text[:5000]
            + f"\n\nChyba: {e}"
        )


# ============================================================
# KARTA
# ============================================================

def metric(label, value):

    st.markdown(
        f"""
        <div class="card">

            <div class="card-label">
                {label}
            </div>

            <div class="card-value">
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
    "Automatický retry při 503"
)


# ============================================================
# HLAVIČKA
# ============================================================

st.markdown(
    '<div class="main-title">'
    '🚗 AutoCheck CZ'
    '</div>',
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
    "## 📋 Vlož inzerát"
)

ad_text = st.text_area(
    "Celý text inzerátu",
    height=380,
    placeholder=(
        "Zkopíruj sem text z Bazoše, Sauto, "
        "TipCars, Mobile.de nebo jiného bazaru..."
    )
)


# ============================================================
# TLAČÍTKO
# ============================================================

if st.button(
    "🚀 SPUSTIT ANALÝZU",
    type="primary",
    use_container_width=True
):

    if not ad_text.strip():

        st.warning(
            "⚠️ Nejprve vlož text inzerátu."
        )

    else:

        with st.spinner(
            "🔎 Analyzuji automobil..."
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


    if verdict == "KUPUJ":

        css = "green"
        emoji = "🟢"

    elif verdict == "VYJEDNÁVAT":

        css = "yellow"
        emoji = "🟡"

    else:

        css = "red"
        emoji = "🔴"


    st.markdown(
        f"""
        <div class="verdict {css}">

            <div class="verdict-small">
                NÁKUPNÍ VERDIKT
            </div>

            <div class="verdict-title">
                {emoji} {verdict}
            </div>

            <div class="score">
                {score}/10
            </div>

            <div style="font-size:17px;">
                {summary}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # IDENTIFIKACE
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
            car.get(
                "brand",
                ""
            )
            + " "
            + car.get(
                "model",
                ""
            )
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

        for item in equipment:

            st.markdown(
                f"✓ {item}"
            )

    else:

        st.write(
            "Výbava nebyla uvedena."
        )


    # ========================================================
    # TECHNIKA
    # ========================================================

    st.markdown(
        "## ⚙️ Motor a převodovka"
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
            f"{i}. {risk.get('risk', 'Riziko')}"
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
                "**Cena opravy:**"
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
        "## 🤝 Jak srazit cenu"
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
