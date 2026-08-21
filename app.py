import streamlit as st
import requests
import json
import re
from urllib.parse import quote


# ============================================================
# AUTO CHECK CZ
# ============================================================

st.set_page_config(
    page_title="AutoCheck CZ",
    page_icon="🚗",
    layout="wide"
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
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
    border: 1px solid rgba(255,255,255,.10);
}

.green {
    background: linear-gradient(135deg,#0d3327,#10251f);
}

.yellow {
    background: linear-gradient(135deg,#3b3010,#29230f);
}

.red {
    background: linear-gradient(135deg,#3b1515,#291010);
}

.verdict-title {
    font-size: 32px;
    font-weight: 900;
}

.score {
    font-size: 46px;
    font-weight: 900;
}

.card {
    background: #161b26;
    border: 1px solid #252c39;
    border-radius: 16px;
    padding: 20px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "debug" not in st.session_state:
    st.session_state.debug = ""


# ============================================================
# API KEY
# ============================================================

def get_api_key():

    try:
        secret = st.secrets.get(
            "GROQ_API_KEY",
            ""
        )
    except Exception:
        secret = ""

    if secret:
        return secret.strip()

    return st.session_state.get(
        "manual_api_key",
        ""
    ).strip()


# ============================================================
# GROQ API
# ============================================================

def groq_call(prompt):

    api_key = get_api_key()

    if not api_key:
        raise Exception(
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
                    "Jsi zkušený český expert na "
                    "ojetá auta. "
                    "Odpovídej přesně a konzervativně."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        "reasoning_effort": "low",

        "max_completion_tokens": 1400,

        "temperature": 0.2,

        "response_format": {
            "type": "json_schema",

            "json_schema": {
                "name": "autocheck",

                "strict": True,

                "schema": {

                    "type": "object",

                    "properties": {

                        "car": {
                            "type": "object",

                            "properties": {

                                "brand": {
                                    "type": ["string", "null"]
                                },

                                "model": {
                                    "type": ["string", "null"]
                                },

                                "year": {
                                    "type": ["integer", "null"]
                                },

                                "mileage_km": {
                                    "type": ["integer", "null"]
                                },

                                "price_czk": {
                                    "type": ["integer", "null"]
                                },

                                "engine": {
                                    "type": ["string", "null"]
                                },

                                "power_kw": {
                                    "type": ["integer", "null"]
                                },

                                "fuel": {
                                    "type": ["string", "null"]
                                },

                                "gearbox": {
                                    "type": ["string", "null"]
                                },

                                "body": {
                                    "type": ["string", "null"]
                                },

                                "drive": {
                                    "type": ["string", "null"]
                                },

                                "equipment": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    }
                                },

                                "seller_claims": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    }
                                }

                            },

                            "required": [
                                "brand",
                                "model",
                                "year",
                                "mileage_km",
                                "price_czk",
                                "engine",
                                "power_kw",
                                "fuel",
                                "gearbox",
                                "body",
                                "drive",
                                "equipment",
                                "seller_claims"
                            ],

                            "additionalProperties": False
                        },

                        "verdict": {
                            "type": "string",

                            "enum": [
                                "KUPUJ",
                                "VYJEDNÁVAT",
                                "RUCE PRYČ"
                            ]
                        },

                        "score": {
                            "type": "number"
                        },

                        "summary": {
                            "type": "string"
                        },

                        "fair_price_low": {
                            "type": "integer"
                        },

                        "fair_price_high": {
                            "type": "integer"
                        },

                        "recommended_max_price": {
                            "type": "integer"
                        },

                        "negotiation_price": {
                            "type": "integer"
                        },

                        "price_score": {
                            "type": "number"
                        },

                        "technical_score": {
                            "type": "number"
                        },

                        "risk_score": {
                            "type": "number"
                        },

                        "technical_summary": {
                            "type": "string"
                        },

                        "weaknesses": {
                            "type": "array",

                            "items": {

                                "type": "object",

                                "properties": {

                                    "title": {
                                        "type": "string"
                                    },

                                    "risk": {
                                        "type": "string"
                                    },

                                    "description": {
                                        "type": "string"
                                    },

                                    "check": {
                                        "type": "string"
                                    }

                                },

                                "required": [
                                    "title",
                                    "risk",
                                    "description",
                                    "check"
                                ],

                                "additionalProperties": False
                            }
                        },

                        "checklist": {
                            "type": "array",

                            "items": {
                                "type": "string"
                            }
                        },

                        "service_low": {
                            "type": "integer"
                        },

                        "service_high": {
                            "type": "integer"
                        },

                        "negotiation_arguments": {
                            "type": "array",

                            "items": {
                                "type": "string"
                            }
                        }

                    },

                    "required": [
                        "car",
                        "verdict",
                        "score",
                        "summary",
                        "fair_price_low",
                        "fair_price_high",
                        "recommended_max_price",
                        "negotiation_price",
                        "price_score",
                        "technical_score",
                        "risk_score",
                        "technical_summary",
                        "weaknesses",
                        "checklist",
                        "service_low",
                        "service_high",
                        "negotiation_arguments"
                    ],

                    "additionalProperties": False
                }
            }
        }
    }

    response = requests.post(
        GROQ_URL,
        headers=headers,
        json=payload,
        timeout=90
    )

    # --------------------------------------------------------
    # RATE LIMIT
    # --------------------------------------------------------

    if response.status_code == 429:

        raise Exception(
            "Groq odmítl požadavek kvůli RATE LIMITU.\n\n"
            + response.text[:2000]
        )

    # --------------------------------------------------------
    # OSTATNÍ API CHYBY
    # --------------------------------------------------------

    if response.status_code != 200:

        raise Exception(
            f"Groq API chyba {response.status_code}:\n\n"
            + response.text[:2000]
        )

    data = response.json()

    st.session_state.debug = json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    )

    try:

        content = data[
            "choices"
        ][0][
            "message"
        ][
            "content"
        ]

    except Exception:

        raise Exception(
            "Groq vrátil neočekávanou odpověď."
        )

    if not content:

        raise Exception(
            "Groq vrátil prázdnou odpověď."
        )

    try:

        return json.loads(content)

    except Exception:

        raise Exception(
            "Groq vrátil neplatný JSON:\n\n"
            + content[:3000]
        )


# ============================================================
# HLAVNÍ AI ANALÝZA
# ============================================================

def analyze_car(ad_text):

    prompt = f"""
Analyzuj následující český automobilový inzerát.

Jsi expert na nákup ojetých automobilů.

DŮLEŽITÉ:

Nevymýšlej údaje, které nejsou uvedené.

Pokud nějaký parametr není známý,
použij null.

Rozlišuj mezi:

- skutečností uvedenou v inzerátu
- typickou slabinou daného auta
- věcí, kterou je nutné ověřit

---

TEXT INZERÁTU:

{ad_text}

---

ÚKOL:

1. Identifikuj konkrétní automobil.

2. Extrahuj:
   - značku
   - model
   - rok
   - nájezd
   - cenu
   - motor
   - výkon
   - palivo
   - převodovku
   - karoserii
   - pohon
   - výbavu

3. Vypiš tvrzení prodejce.

4. Zhodnoť technické riziko konkrétního motoru
   a převodovky.

5. Uveď typické slabiny.

6. U každé slabiny napiš,
   jak ji ověřit při prohlídce.

7. Vytvoř checklist před koupí.

8. Odhadni férovou cenu.

9. Navrhni:
   - maximální cenu
   - cenu, na kterou začít vyjednávat

10. Odhadni servisní náklady
    na následující 2 roky.

11. Dej finální verdikt:

KUPUJ
VYJEDNÁVAT
RUCE PRYČ

Buď konzervativní.

Pokud nemáš dost informací,
výslovně počítej s nejistotou.

Nevydávej tvrzení prodejce
za ověřený fakt.

Celkový výstup musí být stručný,
ale praktický pro člověka,
který chce auto skutečně koupit.
"""

    return groq_call(prompt)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "⚙️ Nastavení"
)

try:

    secret_key = st.secrets.get(
        "GROQ_API_KEY",
        ""
    )

except Exception:

    secret_key = ""

api_key = st.sidebar.text_input(
    "Groq API Key",
    value=secret_key,
    type="password"
)

st.session_state.manual_api_key = api_key

st.sidebar.markdown("---")

st.sidebar.write(
    "Model:"
)

st.sidebar.code(
    MODEL
)

st.sidebar.write(
    "AI požadavků na jedno auto:"
)

st.sidebar.success(
    "1"
)


# ============================================================
# HLAVNÍ STRÁNKA
# ============================================================

st.markdown(
    '<div class="main-title">'
    '🚗 AutoCheck CZ'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Expertní analýza ojetého auta před koupí'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# INZERÁT
# ============================================================

st.markdown(
    "## 📋 Vlož text inzerátu"
)

ad_text = st.text_area(
    "Celý text inzerátu",
    height=300,
    placeholder=(
        "Zkopíruj sem celý inzerát "
        "z Bazoše, Sauto, TipCars apod."
    )
)


# ============================================================
# ANALÝZA
# ============================================================

if st.button(
    "🚀 SPUSTIT ANALÝZU",
    type="primary",
    use_container_width=True
):

    if not api_key:

        st.error(
            "❌ Nejdříve zadej Groq API Key."
        )

    elif not ad_text.strip():

        st.warning(
            "⚠️ Vlož text automobilového inzerátu."
        )

    else:

        with st.spinner(
            "🤖 AI analyzuje automobil..."
        ):

            try:

                result = analyze_car(
                    ad_text
                )

                st.session_state.analysis = result

                st.success(
                    "✅ Analýza dokončena."
                )

            except Exception as e:

                st.error(
                    f"❌ {e}"
                )

                if st.session_state.debug:

                    with st.expander(
                        "🔧 Technická diagnostika"
                    ):

                        st.code(
                            st.session_state.debug
                        )


# ============================================================
# VÝSLEDEK
# ============================================================

if st.session_state.analysis:

    result = st.session_state.analysis

    car = result["car"]

    verdict = result["verdict"]

    score = result["score"]

    # --------------------------------------------------------
    # BARVA VERDIKTU
    # --------------------------------------------------------

    if verdict == "KUPUJ":

        css = "green"
        emoji = "🟢"

    elif verdict == "RUCE PRYČ":

        css = "red"
        emoji = "🔴"

    else:

        css = "yellow"
        emoji = "🟡"

    st.markdown("---")

    # --------------------------------------------------------
    # VERDIKT
    # --------------------------------------------------------

    st.markdown(
        f"""
        <div class="verdict {css}">

            <div style="
                color:#9aa5b8;
                font-size:15px;
            ">
                NÁKUPNÍ VERDIKT
            </div>

            <div class="verdict-title">
                {emoji} {verdict}
            </div>

            <div class="score">
                {score:.1f}/10
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    st.info(
        result["summary"]
    )

    # --------------------------------------------------------
    # AUTO
    # --------------------------------------------------------

    st.markdown(
        "## 🚘 Identifikace vozidla"
    )

    cols = st.columns(4)

    with cols[0]:

        st.metric(
            "Model",
            (
                f"{car.get('brand') or ''} "
                f"{car.get('model') or ''}"
            ).strip()
        )

    with cols[1]:

        st.metric(
            "Rok",
            car.get("year") or "-"
        )

    with cols[2]:

        km = car.get(
            "mileage_km"
        )

        st.metric(
            "Nájezd",
            f"{km:,} km"
            if km
            else "-"
        )

    with cols[3]:

        price = car.get(
            "price_czk"
        )

        st.metric(
            "Cena",
            f"{price:,} Kč"
            if price
            else "-"
        )

    # --------------------------------------------------------
    # TECHNICKÉ PARAMETRY
    # --------------------------------------------------------

    st.markdown(
        "### ⚙️ Technické údaje"
    )

    cols = st.columns(4)

    with cols[0]:

        st.write(
            "**Motor**"
        )

        st.write(
            car.get("engine") or "-"
        )

    with cols[1]:

        st.write(
            "**Výkon**"
        )

        power = car.get(
            "power_kw"
        )

        st.write(
            f"{power} kW"
            if power
            else "-"
        )

    with cols[2]:

        st.write(
            "**Převodovka**"
        )

        st.write(
            car.get("gearbox") or "-"
        )

    with cols[3]:

        st.write(
            "**Palivo**"
        )

        st.write(
            car.get("fuel") or "-"
        )

    # --------------------------------------------------------
    # HODNOCENÍ
    # --------------------------------------------------------

    st.markdown("---")

    st.markdown(
        "## 📊 Hodnocení"
    )

    cols = st.columns(3)

    with cols[0]:

        st.metric(
            "💰 Cena",
            f"{result['price_score']}/10"
        )

    with cols[1]:

        st.metric(
            "⚙️ Technika",
            f"{result['technical_score']}/10"
        )

    with cols[2]:

        st.metric(
            "⚠️ Riziko",
            f"{result['risk_score']}/10"
        )

    # --------------------------------------------------------
    # CENA
    # --------------------------------------------------------

    st.markdown("---")

    st.markdown(
        "## 💰 Tržní a cenové hodnocení"
    )

    cols = st.columns(3)

    with cols[0]:

        st.metric(
            "Férová cena",
            (
                f"{result['fair_price_low']:,} – "
                f"{result['fair_price_high']:,} Kč"
            )
        )

    with cols[1]:

        st.metric(
            "Doporučené maximum",
            f"{result['recommended_max_price']:,} Kč"
        )

    with cols[2]:

        st.metric(
            "Cíl vyjednávání",
            f"{result['negotiation_price']:,} Kč"
        )

    # --------------------------------------------------------
    # TECHNICKÁ ANALÝZA
    # --------------------------------------------------------

    st.markdown("---")

    st.markdown(
        "## ⚙️ Technická analýza"
    )

    st.write(
        result["technical_summary"]
    )

    # --------------------------------------------------------
    # SLABINY
    # --------------------------------------------------------

    st.markdown(
        "### ⚠️ Typické slabiny"
    )

    for weakness in result[
        "weaknesses"
    ]:

        with st.expander(
            f"{weakness['title']} — "
            f"{weakness['risk']}"
        ):

            st.write(
                weakness["description"]
            )

            st.markdown(
                "**Jak ověřit:**"
            )

            st.write(
                weakness["check"]
            )

    # --------------------------------------------------------
    # CHECKLIST
    # --------------------------------------------------------

    st.markdown("---")

    st.markdown(
        "## 🔍 Checklist před koupí"
    )

    for i, item in enumerate(
        result["checklist"]
    ):

        st.checkbox(
            item,
            key=f"inspection_{i}"
        )

    # --------------------------------------------------------
    # SERVIS
    # --------------------------------------------------------

    st.markdown("---")

    st.markdown(
        "## 🔧 Odhad servisu"
    )

    st.metric(
        "Následující 2 roky",
        (
            f"{result['service_low']:,} – "
            f"{result['service_high']:,} Kč"
        )
    )

    # --------------------------------------------------------
    # VÝBAVA
    # --------------------------------------------------------

    st.markdown("---")

    st.markdown(
        "## 🛡️ Výbava"
    )

    equipment = car.get(
        "equipment",
        []
    )

    if equipment:

        for item in equipment:

            st.markdown(
                f"- ✅ {item}"
            )

    else:

        st.write(
            "Výbava nebyla v inzerátu "
            "jednoznačně uvedena."
        )

    # --------------------------------------------------------
    # TVRZENÍ PRODEJCE
    # --------------------------------------------------------

    claims = car.get(
        "seller_claims",
        []
    )

    if claims:

        st.markdown("---")

        st.markdown(
            "## ⚠️ Tvrzení prodejce"
        )

        for claim in claims:

            st.warning(
                claim
            )

    # --------------------------------------------------------
    # VYJEDNÁVÁNÍ
    # --------------------------------------------------------

    st.markdown("---")

    st.markdown(
        "## 🤝 Jak vyjednávat"
    )

    for argument in result[
        "negotiation_arguments"
    ]:

        st.markdown(
            f"- 💬 {argument}"
        )


# ============================================================
# PATIČKA
# ============================================================

st.markdown("---")

st.caption(
    "AutoCheck CZ – experimentální MVP. "
    "AI výsledek nenahrazuje fyzickou kontrolu "
    "vozu, diagnostiku ani ověření VIN."
)
