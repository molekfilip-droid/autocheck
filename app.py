import streamlit as st
from google import genai
from google.genai import types
import json
import time


# ============================================================
# AUTO CHECK CZ
# Profesionální nákupní audit ojetého automobilu
# ============================================================

st.set_page_config(
    page_title="AutoCheck CZ",
    page_icon="🚗",
    layout="wide"
)


# ============================================================
# MODEL
# ============================================================

MODEL = "gemini-2.5-flash"


# ============================================================
# VZHLED
# ============================================================

st.markdown("""
<style>

.block-container {
    max-width: 1450px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

.big-title {
    font-size: 44px;
    font-weight: 800;
    letter-spacing: -1px;
    margin-bottom: 0;
}

.subtitle {
    color: #9aa5b8;
    font-size: 18px;
    margin-bottom: 25px;
}

.section-title {
    margin-top: 10px;
}

.info-card {
    padding: 16px;
    border-radius: 12px;
    border: 1px solid rgba(128,128,128,0.18);
    margin-bottom: 12px;
}

.small-label {
    color: #8d99aa;
    font-size: 13px;
    margin-bottom: 5px;
}

.big-value {
    font-size: 20px;
    font-weight: 700;
    line-height: 1.35;
    overflow-wrap: anywhere;
}

.verdict-box {
    padding: 25px;
    border-radius: 16px;
    border: 1px solid rgba(128,128,128,0.2);
    margin-bottom: 20px;
}

.verdict-small {
    color: #9aa5b8;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 1px;
}

.verdict-title {
    font-size: 34px;
    font-weight: 800;
    margin-top: 5px;
}

.verdict-score {
    font-size: 26px;
    font-weight: 700;
    margin-top: 5px;
}

.highlight-card {
    padding: 20px;
    border-radius: 14px;
    border: 1px solid rgba(128,128,128,0.2);
    min-height: 120px;
}

.highlight-label {
    color: #9aa5b8;
    font-size: 14px;
}

.highlight-value {
    font-size: 26px;
    font-weight: 800;
    margin-top: 8px;
    overflow-wrap: anywhere;
}

.redflag {
    padding: 15px;
    border-radius: 10px;
    border: 1px solid rgba(255,80,80,0.25);
    margin-bottom: 10px;
}

.goodflag {
    padding: 15px;
    border-radius: 10px;
    border: 1px solid rgba(70,180,100,0.25);
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
            "Není nastaven GEMINI_API_KEY ve Streamlit Secrets."
        )

    if not api_key:
        raise Exception(
            "GEMINI_API_KEY je prázdný."
        )

    return api_key.strip()


# ============================================================
# JSON SCHEMA
# ============================================================

ANALYSIS_SCHEMA = {

    "type": "object",

    "properties": {

        # ----------------------------------------------------
        # VERDIKT
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # AUTO
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # VÝBAVA
        # ----------------------------------------------------

        "equipment": {

            "type": "array",

            "items": {
                "type": "string"
            }
        },

        # ----------------------------------------------------
        # CENA
        # ----------------------------------------------------

        "price_analysis": {

            "type": "object",

            "properties": {

                "fair_price": {"type": "string"},
                "good_buy_price": {"type": "string"},
                "max_price": {"type": "string"},
                "market_difference": {"type": "string"},
                "explanation": {"type": "string"}

            },

            "required": [
                "fair_price",
                "good_buy_price",
                "max_price",
                "market_difference",
                "explanation"
            ]
        },

        # ----------------------------------------------------
        # RED FLAGS
        # ----------------------------------------------------

        "red_flags": {

            "type": "object",

            "properties": {

                "overall": {
                    "type": "string",
                    "enum": [
                        "NÍZKÉ",
                        "STŘEDNÍ",
                        "VYŠŠÍ",
                        "VYSOKÉ"
                    ]
                },

                "items": {

                    "type": "array",

                    "items": {

                        "type": "object",

                        "properties": {

                            "title": {"type": "string"},
                            "severity": {
                                "type": "string",
                                "enum": [
                                    "NÍZKÉ",
                                    "STŘEDNÍ",
                                    "VYSOKÉ"
                                ]
                            },
                            "description": {"type": "string"},
                            "what_to_check": {"type": "string"}

                        },

                        "required": [
                            "title",
                            "severity",
                            "description",
                            "what_to_check"
                        ]
                    }
                },

                "missing_information": {

                    "type": "array",

                    "items": {
                        "type": "string"
                    }
                }

            },

            "required": [
                "overall",
                "items",
                "missing_information"
            ]
        },

        # ----------------------------------------------------
        # ZKUŠENOSTI MAJITELŮ
        # ----------------------------------------------------

        "owner_experience": {

            "type": "object",

            "properties": {

                "reliability": {"type": "string"},
                "engine": {"type": "string"},
                "gearbox": {"type": "string"},
                "comfort": {"type": "string"},
                "consumption": {"type": "string"},
                "service_cost": {"type": "string"},

                "positive": {

                    "type": "array",

                    "items": {
                        "type": "string"
                    }
                },

                "negative": {

                    "type": "array",

                    "items": {
                        "type": "string"
                    }
                },

                "typical_problems": {

                    "type": "array",

                    "items": {
                        "type": "string"
                    }
                },

                "note": {
                    "type": "string"
                }

            },

            "required": [
                "reliability",
                "engine",
                "gearbox",
                "comfort",
                "consumption",
                "service_cost",
                "positive",
                "negative",
                "typical_problems",
                "note"
            ]
        },

        # ----------------------------------------------------
        # REÁLNÁ CENA VLASTNICTVÍ
        # ----------------------------------------------------

        "ownership_cost": {

            "type": "object",

            "properties": {

                "purchase_price": {"type": "string"},
                "normal_service": {"type": "string"},
                "likely_repairs": {"type": "string"},
                "tires_brakes": {"type": "string"},
                "risk_reserve": {"type": "string"},
                "two_year_total": {"type": "string"},
                "explanation": {"type": "string"}

            },

            "required": [
                "purchase_price",
                "normal_service",
                "likely_repairs",
                "tires_brakes",
                "risk_reserve",
                "two_year_total",
                "explanation"
            ]
        },

        # ----------------------------------------------------
        # VYJEDNÁVÁNÍ
        # ----------------------------------------------------

        "negotiation": {

            "type": "object",

            "properties": {

                "opening_offer": {"type": "string"},
                "target_price": {"type": "string"},
                "maximum_price": {"type": "string"},
                "estimated_saving": {"type": "string"},

                "arguments": {

                    "type": "array",

                    "items": {

                        "type": "object",

                        "properties": {

                            "argument": {"type": "string"},
                            "impact": {"type": "string"}

                        },

                        "required": [
                            "argument",
                            "impact"
                        ]
                    }
                }

            },

            "required": [
                "opening_offer",
                "target_price",
                "maximum_price",
                "estimated_saving",
                "arguments"
            ]
        },

        # ----------------------------------------------------
        # MÁM TAM JET?
        # ----------------------------------------------------

        "should_visit": {

            "type": "object",

            "properties": {

                "decision": {
                    "type": "string",
                    "enum": [
                        "ANO",
                        "SPÍŠ ANO",
                        "SPÍŠ NE",
                        "NE"
                    ]
                },

                "reason": {
                    "type": "string"
                },

                "before_trip": {

                    "type": "array",

                    "items": {
                        "type": "string"
                    }
                },

                "at_car": {

                    "type": "array",

                    "items": {
                        "type": "string"
                    }
                }

            },

            "required": [
                "decision",
                "reason",
                "before_trip",
                "at_car"
            ]
        },

        # ----------------------------------------------------
        # TECHNIKA
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # RIZIKA
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # CHECKLIST
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # SERVIS
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # ZÁVĚR
        # ----------------------------------------------------

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
        "red_flags",
        "owner_experience",
        "ownership_cost",
        "negotiation",
        "should_visit",
        "technical",
        "risks",
        "checklist",
        "service",
        "conclusion"
    ]
}


# ============================================================
# AI ANALÝZA
# ============================================================

def analyze_car(ad_text):

    api_key = get_api_key()

    client = genai.Client(
        api_key=api_key
    )

    prompt = f"""
Jsi profesionální český automobilový analytik.

Tvým úkolem je vytvořit praktický předkupní audit ojetého automobilu.
Nechci obecné AI povídání. Chci konkrétní informace, které pomohou
člověku rozhodnout, zda má za automobilem jet a kolik za něj nabídnout.

==================================================
TEXT INZERÁTU
==================================================

{ad_text}

==================================================
DŮLEŽITÁ PRAVIDLA
==================================================

Nevymýšlej údaje, které nejsou známé.

Pokud něco není v inzerátu uvedeno, napiš "neuvedeno".

Velmi důležité:

Nesmíš tvrdit, že máš skutečná data z databáze majitelů,
pokud je nemáš.

Nesmíš vymýšlet počet majitelů, počet recenzí ani konkrétní
statistiky z internetu.

Sekce "Zkušenosti majitelů" proto představuje:
- typické dlouhodobé zkušenosti s danou motorizací,
- typické zkušenosti s danou převodovkou,
- obecně známé silné a slabé stránky dané konfigurace.

Na konci této sekce vždy jasně uveď, že jde o orientační
shrnutí typických zkušeností, nikoliv o skutečný průzkum
konkrétní databáze majitelů.

Stejně tak nevymýšlej skutečná aktuální tržní data.

Cenové rozpětí je odborný orientační odhad založený na
parametrech vozidla a typickém trhu.

==================================================
1. VERDIKT
==================================================

KUPUJ:
Auto je při uvedené ceně velmi zajímavé.

VYJEDNÁVAT:
Auto může být zajímavé, ale cena nebo rizika vyžadují
jednání či důkladnou kontrolu.

RUCE PRYČ:
Auto je vzhledem k ceně nebo rizikům nevhodná koupě.

Skóre 1–10.

==================================================
2. CENA
==================================================

Urči:

Férovou cenu.
Dobrou nákupní cenu.
Maximální rozumnou cenu.

Zohledni:
- rok
- nájezd
- motor
- výkon
- převodovku
- výbavu
- karoserii
- pohon
- uvedený stav
- cenu

Uveď také přibližný rozdíl mezi nabídkovou cenou
a odhadovanou férovou cenou.

==================================================
3. RED FLAGS
==================================================

Hledej:

- podezřelé údaje
- chybějící informace
- neobvykle vysoký nájezd
- podezřelé formulace
- chybějící servis
- chybějící VIN
- nejasný původ
- nesoulad mezi rokem, nájezdem a cenou
- potenciální technická rizika

Neoznačuj běžnou neuvedenou informaci automaticky jako
velký problém.

==================================================
4. ZKUŠENOSTI MAJITELŮ
==================================================

Uveď typické zkušenosti s:

- spolehlivostí
- motorem
- převodovkou
- komfortem
- spotřebou
- servisními náklady

Potom:

Co majitelé typicky chválí.

Co typicky kritizují.

Typické problémy.

NIKDY nevymýšlej počet recenzí nebo počet majitelů.

==================================================
5. REÁLNÁ CENA VLASTNICTVÍ
==================================================

Spočítej orientačně:

- kupní cenu
- běžný servis
- pravděpodobné opravy
- pneumatiky/brzdy
- rizikovou rezervu

A odhadni celkové náklady během 2 let.

Pokud nejsou některé informace známé,
pracuj s rozumným rozpětím.

==================================================
6. VYJEDNÁVÁNÍ
==================================================

Navrhni:

STARTOVACÍ NABÍDKU
CÍLOVOU CENU
MAXIMÁLNÍ CENU

A konkrétní argumenty.

Každý argument musí být reálný a vycházet z údajů
v inzerátu nebo z typického servisního rizika.

==================================================
7. MÁM TAM JET?
==================================================

Vyhodnoť:

ANO
SPÍŠ ANO
SPÍŠ NE
NE

A vysvětli proč.

Potom napiš:

Co si vyžádat před cestou.

Co zkontrolovat přímo u auta.

==================================================
8. TECHNICKÁ ANALÝZA
==================================================

Analyzuj konkrétní motor a převodovku.

Podle relevantnosti řeš:

- rozvody
- turbo
- vstřiky
- olej
- chlazení
- DPF
- EGR
- AdBlue
- dvouhmotu
- spojku
- DSG
- automat
- podvozek
- elektroniku

==================================================
9. RIZIKA
==================================================

Uveď nejdůležitější rizika.

U každého:

- problém
- projevy
- ověření
- orientační cena opravy

==================================================
10. CHECKLIST
==================================================

Vytvoř praktický checklist před koupí.

==================================================
11. SERVIS
==================================================

Odhad:

- běžný servis
- pravděpodobné opravy
- špatný scénář
- celkem za 2 roky

==================================================
12. ZÁVĚR
==================================================

Napiš jednoznačně:

- zda bys auto koupil
- za jakou cenu
- co musí kupující před koupí ověřit

==================================================
VÝSTUP
==================================================

Vrať POUZE validní JSON podle zadaného schématu.

Žádný Markdown.
Žádné HTML.
Žádné ```json.
Žádný text před JSON.
Žádný text za JSON.
"""


    max_attempts = 3

    last_error = None

    for attempt in range(max_attempts):

        try:

            response = client.models.generate_content(

                model=MODEL,

                contents=prompt,

                config=types.GenerateContentConfig(

                    response_mime_type="application/json",

                    response_schema=ANALYSIS_SCHEMA,

                    temperature=0.2,

                    max_output_tokens=7000
                )
            )

            if not response.text:

                raise Exception(
                    "Služba vrátila prázdnou odpověď."
                )

            return json.loads(
                response.text
            )

        except Exception as e:

            last_error = e

            if attempt < max_attempts - 1:

                time.sleep(
                    4 * (attempt + 1)
                )

            else:

                raise Exception(
                    "Analýzu se nepodařilo dokončit.\n\n"
                    f"Technická informace: {last_error}"
                )


# ============================================================
# POMOCNÉ FUNKCE
# ============================================================

def info_card(label, value):

    st.markdown(
        f"""
        <div class="info-card">
            <div class="small-label">{label}</div>
            <div class="big-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def score_card(label, value):

    with st.container(border=True):

        st.caption(label)

        st.markdown(
            f"### {value}"
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
    'Profesionální nákupní audit ojetého automobilu'
    '</div>',
    unsafe_allow_html=True
)

st.caption(
    "Technická rizika • Cena • Servis • Vyjednávání • Nákupní verdikt"
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "🚗 AutoCheck CZ"
)

st.sidebar.success(
    "Profesionální analýza připravena"
)

st.sidebar.markdown("---")

st.sidebar.markdown(
    """
### Co AutoCheck vyhodnotí

✓ Nákupní verdikt

✓ Férovou cenu

✓ Red Flags

✓ Typické zkušenosti

✓ Reálné náklady vlastnictví

✓ Vyjednávací taktiku

✓ Technická rizika

✓ Checklist

✓ Doporučení, zda jet na prohlídku
"""
)

st.sidebar.markdown("---")

st.sidebar.caption(
    "Rozhodovací nástroj pro nákup ojetého vozu"
)


# ============================================================
# VSTUP
# ============================================================

st.markdown(
    "## 📋 Vstupní data"
)

st.write(
    "Vlož kompletní text automobilového inzerátu. "
    "AutoCheck z něj automaticky vytáhne důležité údaje "
    "a vytvoří předkupní audit."
)

ad_text = st.text_area(

    "Text inzerátu",

    height=380,

    placeholder=(
        "Zkopíruj sem celý text inzerátu "
        "z Bazoše, Sauto, TipCars, Mobile.de apod."
    ),

    label_visibility="collapsed"
)


# ============================================================
# SPUŠTĚNÍ
# ============================================================

if st.button(
    "🔎 VYTVOŘIT PROFESIONÁLNÍ POSUDEK",
    type="primary",
    use_container_width=True
):

    if not ad_text.strip():

        st.warning(
            "Nejdříve vlož text automobilového inzerátu."
        )

    else:

        with st.spinner(
            "Probíhá profesionální analýza vozidla..."
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


    st.markdown("---")

    st.markdown(
        """
        <div class="verdict-box">
            <div class="verdict-small">
                NÁKUPNÍ VERDIKT
            </div>
        """,
        unsafe_allow_html=True
    )


    if verdict == "KUPUJ":

        st.markdown(
            f"""
            <div class="verdict-title">
                🟢 KUPUJ
            </div>
            <div class="verdict-score">
                {score}/10
            </div>
            """,
            unsafe_allow_html=True
        )

    elif verdict == "VYJEDNÁVAT":

        st.markdown(
            f"""
            <div class="verdict-title">
                🟡 VYJEDNÁVAT
            </div>
            <div class="verdict-score">
                {score}/10
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            f"""
            <div class="verdict-title">
                🔴 RUCE PRYČ
            </div>
            <div class="verdict-score">
                {score}/10
            </div>
            """,
            unsafe_allow_html=True
        )


    st.markdown(
        "</div>",
        unsafe_allow_html=True
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

    st.markdown("---")

    st.markdown(
        "## 🚘 Identifikace vozidla"
    )

    car = data.get(
        "car",
        {}
    )


    c1, c2, c3 = st.columns(3)


    with c1:

        info_card(
            "Model",
            (
                car.get("brand", "")
                + " "
                + car.get("model", "")
            ).strip()
            or "Neuvedeno"
        )

        info_card(
            "Motor",
            car.get(
                "engine",
                "Neuvedeno"
            )
        )

        info_card(
            "Palivo",
            car.get(
                "fuel",
                "Neuvedeno"
            )
        )


    with c2:

        info_card(
            "Rok",
            car.get(
                "year",
                "Neuvedeno"
            )
        )

        info_card(
            "Převodovka",
            car.get(
                "gearbox",
                "Neuvedeno"
            )
        )

        info_card(
            "Nájezd",
            car.get(
                "mileage",
                "Neuvedeno"
            )
        )


    with c3:

        info_card(
            "Cena",
            car.get(
                "price",
                "Neuvedeno"
            )
        )

        info_card(
            "Výkon",
            car.get(
                "power",
                "Neuvedeno"
            )
        )

        info_card(
            "Pohon",
            car.get(
                "drive",
                "Neuvedeno"
            )
        )


    # ========================================================
    # CENA
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 💰 Hodnocení ceny"
    )

    price = data.get(
        "price_analysis",
        {}
    )


    p1, p2, p3 = st.columns(3)


    with p1:

        score_card(
            "Férová cena",
            price.get(
                "fair_price",
                "Neuvedeno"
            )
        )


    with p2:

        score_card(
            "Dobrá nákupní cena",
            price.get(
                "good_buy_price",
                "Neuvedeno"
            )
        )


    with p3:

        score_card(
            "Maximální cena",
            price.get(
                "max_price",
                "Neuvedeno"
            )
        )


    st.info(
        "Rozdíl vůči odhadované tržní hodnotě: "
        + price.get(
            "market_difference",
            "Neuvedeno"
        )
    )


    st.markdown(
        "### Cenový komentář"
    )

    st.write(
        price.get(
            "explanation",
            ""
        )
    )


    # ========================================================
    # RED FLAGS
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 🚩 Red Flags"
    )

    red_flags = data.get(
        "red_flags",
        {}
    )


    overall = red_flags.get(
        "overall",
        "STŘEDNÍ"
    )


    if overall == "NÍZKÉ":

        st.success(
            "🟢 Celková úroveň rizika: NÍZKÁ"
        )

    elif overall == "STŘEDNÍ":

        st.warning(
            "🟡 Celková úroveň rizika: STŘEDNÍ"
        )

    elif overall == "VYŠŠÍ":

        st.warning(
            "🟠 Celková úroveň rizika: VYŠŠÍ"
        )

    else:

        st.error(
            "🔴 Celková úroveň rizika: VYSOKÁ"
        )


    for flag in red_flags.get(
        "items",
        []
    ):

        severity = flag.get(
            "severity",
            "STŘEDNÍ"
        )

        if severity == "VYSOKÉ":

            st.error(
                f"🔴 **{flag.get('title', '')}**\n\n"
                f"{flag.get('description', '')}\n\n"
                f"**Ověřit:** "
                f"{flag.get('what_to_check', '')}"
            )

        elif severity == "STŘEDNÍ":

            st.warning(
                f"🟡 **{flag.get('title', '')}**\n\n"
                f"{flag.get('description', '')}\n\n"
                f"**Ověřit:** "
                f"{flag.get('what_to_check', '')}"
            )

        else:

            st.info(
                f"🟢 **{flag.get('title', '')}**\n\n"
                f"{flag.get('description', '')}\n\n"
                f"**Ověřit:** "
                f"{flag.get('what_to_check', '')}"
            )


    missing = red_flags.get(
        "missing_information",
        []
    )


    if missing:

        st.markdown(
            "### Co v inzerátu chybí"
        )

        for item in missing:

            st.markdown(
                f"• {item}"
            )


    # ========================================================
    # ZKUŠENOSTI MAJITELŮ
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## ⭐ Zkušenosti s touto konfigurací"
    )

    st.caption(
        "Orientační shrnutí typických dlouhodobých zkušeností "
        "s daným modelem, motorem a převodovkou. "
        "Nejde o statistiku konkrétní databáze majitelů."
    )


    owners = data.get(
        "owner_experience",
        {}
    )


    o1, o2, o3 = st.columns(3)


    with o1:

        score_card(
            "Spolehlivost",
            owners.get(
                "reliability",
                "Neuvedeno"
            )
        )

        score_card(
            "Motor",
            owners.get(
                "engine",
                "Neuvedeno"
            )
        )


    with o2:

        score_card(
            "Převodovka",
            owners.get(
                "gearbox",
                "Neuvedeno"
            )
        )

        score_card(
            "Komfort",
            owners.get(
                "comfort",
                "Neuvedeno"
            )
        )


    with o3:

        score_card(
            "Spotřeba",
            owners.get(
                "consumption",
                "Neuvedeno"
            )
        )

        score_card(
            "Servisní náklady",
            owners.get(
                "service_cost",
                "Neuvedeno"
            )
        )


    oc1, oc2 = st.columns(2)


    with oc1:

        st.markdown(
            "### 🟢 Co se typicky chválí"
        )

        for item in owners.get(
            "positive",
            []
        ):

            st.markdown(
                f"✓ {item}"
            )


    with oc2:

        st.markdown(
            "### 🔴 Co se typicky kritizuje"
        )

        for item in owners.get(
            "negative",
            []
        ):

            st.markdown(
                f"• {item}"
            )


    st.markdown(
        "### ⚠️ Typické problémy"
    )

    for item in owners.get(
        "typical_problems",
        []
    ):

        st.markdown(
            f"• {item}"
        )


    st.caption(
        owners.get(
            "note",
            ""
        )
    )


    # ========================================================
    # REÁLNÁ CENA VLASTNICTVÍ
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 💰 Reálná cena vlastnictví"
    )

    st.caption(
        "Orientační odhad toho, kolik může automobil skutečně "
        "stát během prvních dvou let vlastnictví."
    )


    ownership = data.get(
        "ownership_cost",
        {}
    )


    a1, a2, a3 = st.columns(3)


    with a1:

        score_card(
            "Kupní cena",
            ownership.get(
                "purchase_price",
                "Neuvedeno"
            )
        )

        score_card(
            "Běžný servis",
            ownership.get(
                "normal_service",
                "Neuvedeno"
            )
        )


    with a2:

        score_card(
            "Pravděpodobné opravy",
            ownership.get(
                "likely_repairs",
                "Neuvedeno"
            )
        )

        score_card(
            "Pneumatiky / brzdy",
            ownership.get(
                "tires_brakes",
                "Neuvedeno"
            )
        )


    with a3:

        score_card(
            "Riziková rezerva",
            ownership.get(
                "risk_reserve",
                "Neuvedeno"
            )
        )

        with st.container(border=True):

            st.caption(
                "CELKEM / 2 ROKY"
            )

            st.markdown(
                f"## {ownership.get(
                    'two_year_total',
                    'Neuvedeno'
                )}"
            )


    st.write(
        ownership.get(
            "explanation",
            ""
        )
    )


    # ========================================================
    # VYJEDNÁVÁNÍ
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 🤝 Vyjednávací kalkulačka"
    )

    negotiation = data.get(
        "negotiation",
        {}
    )


    n1, n2, n3 = st.columns(3)


    with n1:

        score_card(
            "Začít nabídkou",
            negotiation.get(
                "opening_offer",
                "Neuvedeno"
            )
        )


    with n2:

        score_card(
            "Cílová cena",
            negotiation.get(
                "target_price",
                "Neuvedeno"
            )
        )


    with n3:

        score_card(
            "Maximální cena",
            negotiation.get(
                "maximum_price",
                "Neuvedeno"
            )
        )


    st.success(
        "💰 Odhadovaný prostor pro úsporu: "
        + negotiation.get(
            "estimated_saving",
            "Neuvedeno"
        )
    )


    st.markdown(
        "### 🎯 Argumenty pro vyjednávání"
    )


    for i, argument in enumerate(
        negotiation.get(
            "arguments",
            []
        ),
        start=1
    ):

        with st.container(border=True):

            st.markdown(
                f"**{i}. {argument.get('argument', '')}**"
            )

            st.caption(
                "Dopad na cenu: "
                + argument.get(
                    "impact",
                    "Neuvedeno"
                )
            )


    # ========================================================
    # MÁM TAM JET?
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 🏃 Mám tam jet?"
    )

    visit = data.get(
        "should_visit",
        {}
    )


    decision = visit.get(
        "decision",
        "SPÍŠ ANO"
    )


    if decision == "ANO":

        st.success(
            "🟢 **ANO – auto stojí za osobní prohlídku.**"
        )

    elif decision == "SPÍŠ ANO":

        st.success(
            "🟢 **SPÍŠ ANO – prohlídka dává smysl, "
            "ale před cestou ověř několik věcí.**"
        )

    elif decision == "SPÍŠ NE":

        st.warning(
            "🟠 **SPÍŠ NE – před cestou si vyžádej "
            "další informace.**"
        )

    else:

        st.error(
            "🔴 **NE – podle dostupných údajů "
            "nemá smysl za autem jezdit.**"
        )


    st.markdown(
        "### Proč?"
    )

    st.write(
        visit.get(
            "reason",
            ""
        )
    )


    vc1, vc2 = st.columns(2)


    with vc1:

        st.markdown(
            "### 📞 Před cestou si vyžádej"
        )

        for item in visit.get(
            "before_trip",
            []
        ):

            st.markdown(
                f"☐ {item}"
            )


    with vc2:

        st.markdown(
            "### 🔍 Přímo u auta zkontroluj"
        )

        for item in visit.get(
            "at_car",
            []
        ):

            st.markdown(
                f"☐ {item}"
            )


    # ========================================================
    # VÝBAVA
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 🛡️ Výbava"
    )


    equipment = data.get(
        "equipment",
        []
    )


    if equipment:

        e1, e2 = st.columns(2)

        for i, item in enumerate(
            equipment
        ):

            if i % 2 == 0:

                with e1:

                    st.markdown(
                        f"✓ {item}"
                    )

            else:

                with e2:

                    st.markdown(
                        f"✓ {item}"
                    )

    else:

        st.info(
            "Výbava nebyla v inzerátu dostatečně uvedena."
        )


    # ========================================================
    # TECHNIKA
    # ========================================================

    st.markdown("---")

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
        "### 🔎 Klíčové body"
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

    st.markdown("---")

    st.markdown(
        "## ⚠️ Technická rizika"
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
                "**Jak se problém projevuje**"
            )

            st.write(
                risk.get(
                    "symptoms",
                    ""
                )
            )

            st.markdown(
                "**Jak ho ověřit**"
            )

            st.write(
                risk.get(
                    "verification",
                    ""
                )
            )

            st.markdown(
                "**Orientační cena opravy**"
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

    st.markdown("---")

    st.markdown(
        "## 🔍 Checklist před koupí"
    )

    st.caption(
        "Vezmi si tento seznam s sebou na prohlídku."
    )


    checklist = data.get(
        "checklist",
        []
    )


    for i, item in enumerate(
        checklist,
        start=1
    ):

        with st.expander(
            f"{i}. {item.get('item', '')}"
        ):

            st.write(
                item.get(
                    "why",
                    ""
                )
            )


    # ========================================================
    # SERVIS
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 🔧 Odhad servisních nákladů"
    )


    service = data.get(
        "service",
        {}
    )


    s1, s2, s3, s4 = st.columns(4)


    with s1:

        score_card(
            "Běžný servis",
            service.get(
                "normal",
                "Neuvedeno"
            )
        )


    with s2:

        score_card(
            "Pravděpodobné opravy",
            service.get(
                "likely_repairs",
                "Neuvedeno"
            )
        )


    with s3:

        score_card(
            "Špatný scénář",
            service.get(
                "worst_case",
                "Neuvedeno"
            )
        )


    with s4:

        score_card(
            "Celkem / 2 roky",
            service.get(
                "two_year_total",
                "Neuvedeno"
            )
        )


    # ========================================================
    # FINÁLNÍ DOPORUČENÍ
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 🏆 Finální doporučení"
    )


    st.info(
        data.get(
            "conclusion",
            ""
        )
    )


    # ========================================================
    # SKÓRE
    # ========================================================

    st.markdown("---")

    st.markdown(
        "### 📊 Celkové skóre"
    )


    try:

        score_number = int(score)

        score_number = max(
            0,
            min(
                score_number,
                10
            )
        )

        st.progress(
            score_number / 10
        )

        st.markdown(
            f"### {score_number}/10"
        )

    except Exception:

        st.write(
            f"Skóre: {score}/10"
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "AutoCheck CZ • Profesionální předkupní automobilový audit"
)

st.caption(
    "Výsledek je podpůrný nástroj pro rozhodování. "
    "Nenahrazuje fyzickou prohlídku, diagnostiku ani "
    "ověření historie vozidla."
)
