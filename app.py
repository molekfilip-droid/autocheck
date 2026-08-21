import streamlit as st
from google import genai
from google.genai import types


# ============================================================
# AUTO CHECK CZ
# ============================================================

st.set_page_config(
    page_title="AutoCheck CZ",
    page_icon="🚗",
    layout="wide"
)

MODEL = "gemini-3.5-flash"


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
    border: 1px solid rgba(255,255,255,.12);
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
    font-size: 42px;
    font-weight: 900;
}

.info {
    padding: 15px;
    border-radius: 12px;
    background: rgba(255,255,255,.04);
    margin-bottom: 10px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# GEMINI API KEY ZE STREAMLIT SECRETS
# ============================================================

def get_api_key():

    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        raise Exception(
            "Chybí GEMINI_API_KEY ve Streamlit Secrets.\n\n"
            "Otevři nastavení aplikace na Streamlit Cloud → "
            "Settings → Secrets a vlož:\n\n"
            'GEMINI_API_KEY = "tvůj_api_klíč"'
        )

    if not api_key:
        raise Exception(
            "GEMINI_API_KEY ve Secrets je prázdný."
        )

    return api_key.strip()


# ============================================================
# GEMINI REQUEST
# ============================================================

def ask_gemini(prompt):

    api_key = get_api_key()

    try:

        client = genai.Client(
            api_key=api_key
        )

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1800,
                system_instruction="""
Jsi zkušený český odborník na ojetá auta.

Tvým úkolem je pomáhat kupujícímu rozhodnout,
zda konkrétní ojeté auto stojí za koupi.

Piš česky.
Buď konkrétní.
Nevymýšlej si údaje.
Pokud něco není známé, napiš "neuvedeno".

Rozlišuj mezi:
1. údaji uvedenými v inzerátu
2. typickými vlastnostmi daného modelu
3. věcmi, které je nutné fyzicky ověřit.

Nikdy netvrď, že konkrétní auto má závadu,
pokud to z poskytnutých informací nelze potvrdit.
"""
            )
        )

    except Exception as e:

        raise Exception(
            f"Gemini API chyba:\n\n{e}"
        )


    # ========================================================
    # TEXT ODPOVĚDI
    # ========================================================

    try:

        text = response.text

    except Exception:

        text = None


    if text and text.strip():

        return text.strip()


    # ========================================================
    # DETAILNÍ DIAGNOSTIKA
    # ========================================================

    details = []

    try:

        if response.candidates:

            candidate = response.candidates[0]

            details.append(
                f"Finish reason: "
                f"{candidate.finish_reason}"
            )

            if candidate.safety_ratings:

                details.append(
                    f"Safety ratings: "
                    f"{candidate.safety_ratings}"
                )

    except Exception:

        pass


    raise Exception(
        "Gemini vrátil prázdnou odpověď.\n\n"
        + "\n".join(details)
    )


# ============================================================
# ANALÝZA AUTA
# ============================================================

def analyze_car(ad_text):

    prompt = f"""
Analyzuj tento konkrétní inzerát ojetého automobilu.

==============================
TEXT INZERÁTU
==============================

{ad_text}

==============================
ÚKOL
==============================

Zpracuj praktický nákupní posudek.

Nejde o obecný článek o tomto modelu.
Chci zjistit, zda je DOBRÝ NÁPAD KOUPIT TENTO KONKRÉTNÍ KUS.

Pokud chybí důležité údaje,
výslovně je označ jako "neuvedeno".

==============================
VÝSTUP
==============================

# 🚗 VERDIKT

Vyber jednu možnost:

**KUPUJ**

**VYJEDNÁVAT**

**RUCE PRYČ**

Pod verdiktem vysvětli proč.

# ⭐ SKÓRE

Dej autu hodnocení od 1 do 10.

# 🚘 IDENTIFIKACE

- Značka:
- Model:
- Rok:
- Motor:
- Výkon:
- Palivo:
- Převodovka:
- Pohon:
- Karoserie:
- Nájezd:
- Cena:

# 🛡️ VÝBAVA

Vypiš nejdůležitější výbavu
uvedenou v inzerátu.

# 💰 CENA

Urči pokud možno:

- Férová cena:
- Dobrá nákupní cena:
- Maximální cena, za kterou bys auto koupil:

Vysvětli, jak jsi k hodnocení došel.

Pokud nemáš dost informací pro přesný odhad,
řekni to.

# ⚙️ MOTOR A PŘEVODOVKA

Zhodnoť konkrétní motorizaci
a převodovku.

Uveď:

- spolehlivost
- typické závady
- očekávanou životnost
- drahé komponenty
- co je nutné před koupí ověřit

# ⚠️ HLAVNÍ RIZIKA

Uveď 5 až 8 nejdůležitějších rizik.

U každého:

**Riziko:**
**Jak se projevuje:**
**Jak ověřit:**
**Orientační cena opravy:**

# 🔍 CHECKLIST PROHLÍDKY

Napiš 10 konkrétních bodů,
které má kupující při prohlídce udělat.

Checklist přizpůsob konkrétnímu autu.

# 🔧 SERVIS NA 2 ROKY

Odhadni:

- běžný servis
- pravděpodobné opravy
- rizikový scénář

Uveď částky v Kč.

# 🤝 VYJEDNÁVÁNÍ

Napiš konkrétní argumenty,
kterými může kupující srazit cenu.

Ne obecné rady typu "zkuste smlouvat".

Chci konkrétní argumenty
vyplývající z tohoto inzerátu
nebo daného modelu.

# 🏁 ZÁVĚR

Odpověz:

1. Jel bys toto auto osobně prohlédnout?
2. Co bys kontroloval jako první?
3. Jakou cenu bys považoval za dobrou?
4. Jakou cenu bys už nedal?
5. Za jakých podmínek bys auto koupil?

Buď stručný, ale konkrétní.
"""


    return ask_gemini(prompt)


# ============================================================
# HLAVNÍ NADPIS
# ============================================================

st.markdown(
    '<div class="main-title">🚗 AutoCheck CZ</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Expertní analýza ojetého auta před koupí'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("⚙️ Nastavení")

st.sidebar.success(
    "🔐 API klíč načítán ze Streamlit Secrets"
)

st.sidebar.markdown("---")

st.sidebar.write("AI model:")

st.sidebar.code(
    MODEL
)

st.sidebar.markdown("---")

st.sidebar.caption(
    "Jedna AI analýza = jeden API požadavek."
)


# ============================================================
# VSTUP INZERÁTU
# ============================================================

st.markdown("## 📋 Vlož inzerát")

ad_text = st.text_area(
    "Zkopíruj sem celý text inzerátu",
    height=350,
    placeholder=(
        "Sem vlož text z Bazoše, Sauto, TipCars "
        "nebo autobazaru..."
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

    if not ad_text.strip():

        st.warning(
            "⚠️ Nejdříve vlož text inzerátu."
        )

    else:

        with st.spinner(
            "🤖 Gemini analyzuje automobil..."
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
                    f"❌ {e}"
                )


# ============================================================
# VÝSLEDEK
# ============================================================

if "analysis" in st.session_state:

    result = st.session_state[
        "analysis"
    ]

    st.markdown("---")

    upper = result.upper()


    # ========================================================
    # VERDIKT
    # ========================================================

    if "RUCE PRYČ" in upper:

        verdict = "RUCE PRYČ"
        emoji = "🔴"
        css = "red"

    elif "VYJEDNÁVAT" in upper:

        verdict = "VYJEDNÁVAT"
        emoji = "🟡"
        css = "yellow"

    else:

        verdict = "KUPUJ"
        emoji = "🟢"
        css = "green"


    # ========================================================
    # SKÓRE
    # ========================================================

    score = "?"

    for line in result.splitlines():

        line_clean = line.strip()

        if line_clean.startswith(
            "**SKÓRE**"
        ):

            continue

        if line_clean.startswith(
            "SKÓRE:"
        ):

            score = (
                line_clean
                .split(":", 1)[1]
                .strip()
            )

            break


    # ========================================================
    # VERDIKT BOX
    # ========================================================

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
                {score}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # POSUDEK
    # ========================================================

    st.markdown(
        result
    )


# ============================================================
# PATIČKA
# ============================================================

st.markdown("---")

st.caption(
    "AutoCheck CZ – MVP. "
    "AI analýza nenahrazuje fyzickou kontrolu vozidla, "
    "diagnostiku ani ověření VIN."
)
