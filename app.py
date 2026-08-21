import streamlit as st
import requests
import json


# ============================================================
# AUTO CHECK CZ
# ============================================================

st.set_page_config(
    page_title="AutoCheck CZ",
    page_icon="🚗",
    layout="wide"
)

# MODEL
MODEL = "llama-3.1-8b-instant"

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


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
    font-size: 46px;
    font-weight: 900;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION
# ============================================================

if "analysis" not in st.session_state:
    st.session_state.analysis = None


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
# GROQ
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
                    "Jsi zkušený český expert "
                    "na ojeté automobily. "
                    "Odpovídej česky, věcně a prakticky."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        "temperature": 0.2,

        "max_tokens": 1800
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

        try:
            error = response.json()

            message = error.get(
                "error",
                {}
            ).get(
                "message",
                response.text
            )

        except Exception:
            message = response.text

        raise Exception(
            "Groq RATE LIMIT:\n\n"
            + message
        )

    # --------------------------------------------------------
    # OSTATNÍ CHYBY
    # --------------------------------------------------------

    if response.status_code != 200:

        raise Exception(
            f"Groq API chyba "
            f"{response.status_code}:\n\n"
            f"{response.text[:2000]}"
        )

    data = response.json()

    try:

        return data[
            "choices"
        ][0][
            "message"
        ][
            "content"
        ].strip()

    except Exception:

        raise Exception(
            "Groq vrátil neočekávanou odpověď."
        )


# ============================================================
# ANALÝZA
# ============================================================

def analyze_car(ad_text):

    prompt = f"""
Analyzuj tento inzerát ojetého automobilu.

TEXT INZERÁTU:
{ad_text}

Jsi zkušený český nákupčí ojetých aut.

Potřebuji praktickou analýzu pro člověka,
který zvažuje koupi tohoto konkrétního auta.

NIKDY nevymýšlej údaje, které nejsou v inzerátu.

Pokud údaj neznáš, napiš "neuvedeno".

Použij přesně tuto strukturu:

VERDIKT:
KUPUJ / VYJEDNÁVAT / RUCE PRYČ

SKÓRE:
číslo 1 až 10

AUTO:
značka, model, rok, motor, výkon,
palivo, převodovka, nájezd, cena

VÝBAVA:
stručný seznam důležité výbavy

CENA:
Zhodnoť, jestli cena odpovídá autu.
Uveď:
- odhad férové ceny
- doporučenou maximální cenu
- cenu, na kterou začít vyjednávat

TECHNIKA:
Zhodnoť motor, převodovku a pohon.
Uveď jejich silné a slabé stránky.

RIZIKA:
Uveď nejdůležitější typické závady
a rizika tohoto konkrétního auta.
U každého napiš, jak ho při prohlídce ověřit.

CHECKLIST:
Napiš 8 až 12 konkrétních bodů,
které má kupující při prohlídce zkontrolovat.

SERVIS:
Odhad nákladů na běžný servis
a možné opravy během následujících 2 let.

VYJEDNÁVÁNÍ:
Napiš konkrétní argumenty,
kterými může kupující srazit cenu.

ZÁVĚR:
Jednoduše vysvětli, proč je verdikt
KUPUJ, VYJEDNÁVAT nebo RUCE PRYČ.

Buď konkrétní.
Neopakuj zbytečně text inzerátu.
Pokud něco nelze určit,
jasně to přiznej.
"""

    return groq_call(prompt)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "⚙️ AutoCheck CZ"
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

st.sidebar.write("Použitý model:")

st.sidebar.code(
    MODEL
)

st.sidebar.caption(
    "1 AI požadavek na jednu analýzu"
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
    "## 📋 Vlož inzerát"
)

ad_text = st.text_area(
    "Zkopíruj sem celý text inzerátu",
    height=320,
    placeholder=(
        "Sem vlož text z Bazoše, "
        "Sauto, TipCars nebo jiného autobazaru..."
    )
)


# ============================================================
# SPUŠTĚNÍ
# ============================================================

if st.button(
    "🚀 SPUSTIT ANALÝZU",
    type="primary",
    use_container_width=True
):

    if not api_key:

        st.error(
            "❌ Zadej Groq API Key."
        )

    elif not ad_text.strip():

        st.warning(
            "⚠️ Nejdříve vlož text inzerátu."
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


# ============================================================
# VÝSLEDEK
# ============================================================

if st.session_state.analysis:

    result = st.session_state.analysis

    st.markdown("---")

    # --------------------------------------------------------
    # ZJIŠTĚNÍ VERDIKTU
    # --------------------------------------------------------

    text_upper = result.upper()

    if "RUCE PRYČ" in text_upper:

        verdict = "RUCE PRYČ"
        css = "red"
        emoji = "🔴"

    elif "VYJEDNÁVAT" in text_upper:

        verdict = "VYJEDNÁVAT"
        css = "yellow"
        emoji = "🟡"

    else:

        verdict = "KUPUJ"
        css = "green"
        emoji = "🟢"


    # --------------------------------------------------------
    # SKÓRE
    # --------------------------------------------------------

    score = "?"

    for line in result.splitlines():

        if "SKÓRE:" in line.upper():

            score = (
                line.split(
                    ":",
                    1
                )[1].strip()
            )

            break


    # --------------------------------------------------------
    # VERDIKT BOX
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
                {score}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


    # --------------------------------------------------------
    # VÝSLEDEK
    # --------------------------------------------------------

    st.markdown(
        result
    )


# ============================================================
# PATIČKA
# ============================================================

st.markdown("---")

st.caption(
    "AutoCheck CZ – experimentální MVP. "
    "AI analýza nenahrazuje fyzickou kontrolu "
    "vozidla, diagnostiku ani ověření VIN."
)
