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
    padding-bottom: 4rem;
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

.section-divider {
    margin-top: 35px;
    margin-bottom: 20px;
}

.small-note {
    color: #8d98aa;
    font-size: 14px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# API
# ============================================================

def get_api_key():

    try:

        api_key = st.secrets["GEMINI_API_KEY"]

    except Exception:

        raise Exception(
            "Nastavení služby není kompletní. "
            "Zkontroluj GEMINI_API_KEY ve Streamlit Secrets."
        )

    if not api_key:

        raise Exception(
            "API klíč není nastaven."
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

                "brand": {
                    "type": "string"
                },

                "model": {
                    "type": "string"
                },

                "year": {
                    "type": "string"
                },

                "engine": {
                    "type": "string"
                },

                "power": {
                    "type": "string"
                },

                "fuel": {
                    "type": "string"
                },

                "gearbox": {
                    "type": "string"
                },

                "drive": {
                    "type": "string"
                },

                "body": {
                    "type": "string"
                },

                "mileage": {
                    "type": "string"
                },

                "price": {
                    "type": "string"
                }

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

                "fair_price": {
                    "type": "string"
                },

                "good_buy_price": {
                    "type": "string"
                },

                "max_price": {
                    "type": "string"
                },

                "explanation": {
                    "type": "string"
                }

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

                "engine": {
                    "type": "string"
                },

                "gearbox": {
                    "type": "string"
                },

                "reliability": {
                    "type": "string"
                },

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

                    "risk": {
                        "type": "string"
                    },

                    "symptoms": {
                        "type": "string"
                    },

                    "verification": {
                        "type": "string"
                    },

                    "repair_cost": {
                        "type": "string"
                    }

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

                    "item": {
                        "type": "string"
                    },

                    "why": {
                        "type": "string"
                    }

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

                "normal": {
                    "type": "string"
                },

                "likely_repairs": {
                    "type": "string"
                },

                "worst_case": {
                    "type": "string"
                },

                "two_year_total": {
                    "type": "string"
                }

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
# PROFESIONÁLNÍ ANALÝZA
# ============================================================

def analyze_car(ad_text):

    api_key = get_api_key()

    client = genai.Client(
        api_key=api_key
    )

    prompt = f"""
Jsi profesionální automobilový analytik specializující se
na nákup ojetých vozidel v České republice.

Proveď důkladný nákupní audit automobilu podle textu inzerátu.

==================================================
TEXT INZERÁTU
==================================================

{ad_text}

==================================================
HLAVNÍ ÚKOL
==================================================

Cílem je dát kupujícímu co nejpraktičtější odpověď:

- Je toto auto dobrá koupě?
- Je cena odpovídající?
- Jaká je férová cena?
- Jaká cena by byla opravdu dobrý nákup?
- Jaké jsou největší technické hrozby?
- Co přesně kontrolovat před koupí?
- Kolik může stát servis během dalších 2 let?
- Jaké argumenty použít při vyjednávání?

==================================================
DŮLEŽITÉ
==================================================

Nevymýšlej si údaje o konkrétním vozidle.

Pokud není údaj znám:

"neuvedeno"

Jasně rozlišuj:

1. informace přímo z inzerátu
2. typické vlastnosti daného modelu
3. skutečnosti, které musí kupující ověřit

Pokud je něco pouze pravděpodobné,
neprezentuj to jako jistotu.

==================================================
NÁKUPNÍ VERDIKT
==================================================

KUPUJ

Použij pokud jde o velmi zajímavou nabídku
a rizika jsou přiměřená.

VYJEDNÁVAT

Použij pokud může být auto dobrá koupě,
ale cena nebo určitá rizika vyžadují vyjednávání.

RUCE PRYČ

Použij pokud je auto výrazně předražené,
má zásadní rizika nebo je celkově nevýhodné.

Skóre:

1 = velmi špatná koupě
10 = mimořádně dobrá koupě

==================================================
HODNOCENÍ CENY
==================================================

Stanov:

- Férovou cenu
- Dobrou nákupní cenu
- Maximální rozumnou cenu

Zohledni:

- rok
- nájezd
- motor
- převodovku
- výkon
- výbavu
- karoserii
- pohon
- stáří
- cenu vozidla

Pokud je k dispozici cena bez DPH i s DPH,
zachovej obě hodnoty.

==================================================
TECHNICKÁ ANALÝZA
==================================================

Analyzuj konkrétní motor a převodovku.

Zaměř se na relevantní problémy:

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

Neuváděj nesouvisející problémy.

==================================================
RIZIKA
==================================================

Uveď maximálně 8 nejdůležitějších rizik.

U každého:

- problém
- typické projevy
- způsob ověření
- orientační cena opravy

==================================================
KONTROLNÍ CHECKLIST
==================================================

Vytvoř 10 konkrétních bodů,
které může kupující použít přímo při prohlídce.

Ne obecné rady.

==================================================
SERVIS
==================================================

Odhadni:

- běžný servis
- pravděpodobné opravy
- špatný scénář
- celkové náklady za 2 roky

Uváděj částky v Kč.

==================================================
VYJEDNÁVÁNÍ
==================================================

Vytvoř konkrétní argumenty,
kterými může kupující tlačit cenu dolů.

Pokud je například blížící se servis,
uveď jeho přibližnou hodnotu.

==================================================
KONEČNÉ DOPORUČENÍ
==================================================

Jednoznačně napiš:

- zda bys auto koupil
- za jakou cenu
- proč

==================================================
FORMÁT
==================================================

Vrať pouze validní JSON.

Žádný Markdown.

Žádné HTML.

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

        error = str(e)

        if (
            "503" in error
            or
            "UNAVAILABLE" in error
            or
            "high demand" in error.lower()
        ):

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
                    "Služba je momentálně dočasně nedostupná. "
                    "Zkus analýzu spustit znovu za chvíli.\n\n"
                    f"Technická informace: {e2}"
                )

        else:

            raise e


    if not response.text:

        raise Exception(
            "Nepodařilo se získat výsledek analýzy."
        )


    try:

        return json.loads(
            response.text
        )

    except Exception:

        raise Exception(
            "Výsledek analýzy se nepodařilo zpracovat."
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
    "Technická rizika • Cenová analýza • Servisní náklady • Nákupní taktika"
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "AutoCheck CZ"
)

st.sidebar.success(
    "Analytický systém připraven"
)

st.sidebar.markdown("---")

st.sidebar.markdown(
    "**Co získáš:**"
)

st.sidebar.markdown(
    """
    ✓ Nákupní verdikt

    ✓ Hodnocení ceny

    ✓ Technická rizika

    ✓ Kontrolní checklist

    ✓ Odhad servisu

    ✓ Argumenty pro vyjednávání
    """
)

st.sidebar.markdown("---")

st.sidebar.caption(
    "Profesionální předkupní analýza"
)


# ============================================================
# INZERÁT
# ============================================================

st.markdown(
    "## 📋 Vstupní data"
)

st.write(
    "Vlož kompletní text nabídky. "
    "Čím více údajů inzerát obsahuje, tím přesnější bude posudek."
)

ad_text = st.text_area(
    "Text inzerátu",
    height=400,
    placeholder=(
        "Zkopíruj sem celý text inzerátu "
        "z Bazoše, Sauto, TipCars, Mobile.de apod."
    ),
    label_visibility="collapsed"
)


# ============================================================
# ANALÝZA
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
            "Probíhá odborné vyhodnocení vozidla..."
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
        "## 🏁 Nákupní verdikt"
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

        st.metric(
            "Model",
            (
                car.get("brand", "")
                + " "
                + car.get("model", "")
            ).strip()
            or "Neuvedeno"
        )

        st.metric(
            "Motor",
            car.get(
                "engine",
                "Neuvedeno"
            )
        )

        st.metric(
            "Palivo",
            car.get(
                "fuel",
                "Neuvedeno"
            )
        )


    with c2:

        st.metric(
            "Rok",
            car.get(
                "year",
                "Neuvedeno"
            )
        )

        st.metric(
            "Převodovka",
            car.get(
                "gearbox",
                "Neuvedeno"
            )
        )

        st.metric(
            "Nájezd",
            car.get(
                "mileage",
                "Neuvedeno"
            )
        )


    with c3:

        st.metric(
            "Cena",
            car.get(
                "price",
                "Neuvedeno"
            )
        )

        st.metric(
            "Výkon",
            car.get(
                "power",
                "Neuvedeno"
            )
        )

        st.metric(
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

        st.metric(
            "Férová cena",
            price.get(
                "fair_price",
                "Neuvedeno"
            )
        )


    with p2:

        st.metric(
            "Dobrá nákupní cena",
            price.get(
                "good_buy_price",
                "Neuvedeno"
            )
        )


    with p3:

        st.metric(
            "Maximální cena",
            price.get(
                "max_price",
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

        col1, col2 = st.columns(2)

        for i, item in enumerate(
            equipment
        ):

            if i % 2 == 0:

                with col1:

                    st.markdown(
                        f"✓ {item}"
                    )

            else:

                with col2:

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
        "### 🔎 Klíčové body kontroly"
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

        title = risk.get(
            "risk",
            "Riziko"
        )

        with st.expander(
            f"{i}. {title}"
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
        "Praktický seznam bodů, které je vhodné projít "
        "přímo při prohlídce vozidla."
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
        "## 🔧 Odhad provozních nákladů"
    )

    st.caption(
        "Orientační očekávané náklady během následujících 2 let."
    )


    service = data.get(
        "service",
        {}
    )


    s1, s2, s3, s4 = st.columns(4)


    with s1:

        st.metric(
            "Běžný servis",
            service.get(
                "normal",
                "Neuvedeno"
            )
        )


    with s2:

        st.metric(
            "Pravděpodobné opravy",
            service.get(
                "likely_repairs",
                "Neuvedeno"
            )
        )


    with s3:

        st.metric(
            "Špatný scénář",
            service.get(
                "worst_case",
                "Neuvedeno"
            )
        )


    with s4:

        st.metric(
            "Celkem / 2 roky",
            service.get(
                "two_year_total",
                "Neuvedeno"
            )
        )


    # ========================================================
    # VYJEDNÁVÁNÍ
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 🤝 Nákupní taktika"
    )

    st.caption(
        "Konkrétní argumenty, které lze použít při jednání s prodejcem."
    )


    negotiation = data.get(
        "negotiation",
        []
    )


    for i, item in enumerate(
        negotiation,
        start=1
    ):

        st.markdown(
            f"**{i}.** {item}"
        )


    # ========================================================
    # ZÁVĚR
    # ========================================================

    st.markdown("---")

    st.markdown(
        "## 🏆 Finální doporučení"
    )


    conclusion = data.get(
        "conclusion",
        ""
    )


    st.info(
        conclusion
    )


    # ========================================================
    # HODNOCENÍ
    # ========================================================

    st.markdown("---")

    st.markdown(
        "### Celkové hodnocení"
    )


    st.progress(
        max(
            0,
            min(
                int(score) / 10,
                1
            )
        )
    )

    st.write(
        f"**Celkové skóre: {score}/10**"
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "AutoCheck CZ • Profesionální předkupní automobilový audit"
)

st.caption(
    "Výsledek slouží jako podpůrný nástroj při rozhodování "
    "a nenahrazuje fyzickou prohlídku, diagnostiku ani "
    "ověření historie vozidla."
)
