import streamlit as st
import requests


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
# GROQ REQUEST
# ============================================================

def groq_call(prompt):

    api_key = get_api_key()

    if not api_key:
        raise Exception(
            "Chybí Groq API Key."
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
                    "na ojetá auta. "
                    "Piš česky, konkrétně a prakticky."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        "temperature": 0.2,

        "max_tokens": 1200
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
            data = response.json()

            message = data.get(
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
    # API ERROR
    # --------------------------------------------------------

    if response.status_code != 200:

        raise Exception(
            f"Groq API chyba {response.status_code}:\n\n"
            f"{response.text[:2000]}"
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    data = response.json()

    try:

        content = (
            data["choices"][0]
            ["message"]["content"]
        )

    except Exception:

        raise Exception(
            "Groq vrátil neočekávanou odpověď."
        )

    if not content:

        raise Exception(
            "Groq vrátil prázdnou odpověď."
        )

    return content.strip()


# ============================================================
# ANALÝZA AUTA
# ============================================================

def analyze_car(ad_text):

    prompt = f"""
Analyzuj tento inzerát ojetého automobilu.

TEXT INZERÁTU:
{ad_text}

Jsi odborník na nákup ojetých aut v ČR.

DŮLEŽITÉ:

Nevymýšlej údaje, které nejsou známé.

Pokud něco není uvedeno,
napiš "neuvedeno".

Rozlišuj mezi údaji z inzerátu
a typickými riziky daného modelu.

Vytvoř praktický nákupní posudek.

Použij přesně tuto strukturu:

# VERDIKT

Vyber pouze:

KUPUJ

VYJEDNÁVAT

RUCE PRYČ

## SKÓRE

0–10

## AUTO

Značka:
Model:
Rok:
Motor:
Výkon:
Palivo:
Převodovka:
Nájezd:
Cena:

## VÝBAVA

Vypiš důležitou výbavu.

## 💰 CENA

Uveď:

Férová cena:
Doporučená maximální cena:
Cena pro zahájení vyjednávání:

Krátce vysvětli proč.

## ⚙️ TECHNIKA

Zhodnoť konkrétní motor,
převodovku a pohon.

## ⚠️ RIZIKA

Uveď 5 až 8 nejdůležitějších
rizik tohoto konkrétního auta.

U každého napiš,
jak se dá ověřit.

## 🔍 CHECKLIST

Napiš 10 konkrétních věcí,
které má kupující zkontrolovat
před koupí.

## 🔧 SERVIS

Odhadni běžné servisní náklady
na následující 2 roky.

Uveď rozpětí v Kč.

## 🤝 VYJEDNÁVÁNÍ

Napiš konkrétní argumenty,
kterými může kupující srazit cenu.

## 🏁 ZÁVĚR

V několika větách vysvětli,
jestli bys toto auto osobně jel
prohlédnout a za jakých podmínek
by dávalo smysl ho koupit.

Buď realistický.

Neslibuj jistotu tam,
kde ji z inzerátu nelze zjistit.

Nepopisuj zbytečně obecné informace.
Zaměř se na konkrétní automobil.
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

st.sidebar.write(
    "Použitý model:"
)

st.sidebar.code(
    MODEL
)

st.sidebar.write(
    "AI požadavků na analýzu:"
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
# VSTUP
# ============================================================

st.markdown(
    "## 📋 Vlož inzerát"
)

ad_text = st.text_area(
    "Zkopíruj sem celý text inzerátu",
    height=350,
    placeholder=(
        "Sem vlož celý text z Bazoše, "
        "Sauto, TipCars nebo autobazaru..."
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

    result = st.session_state["analysis"]

    st.markdown("---")

    # --------------------------------------------------------
    # VERDIKT
    # --------------------------------------------------------

    upper = result.upper()

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


    # --------------------------------------------------------
    # SKÓRE
    # --------------------------------------------------------

    score = "?"

    for line in result.splitlines():

        if line.strip().upper().startswith(
            "0–10"
        ):
            continue

        if "SKÓRE" in line.upper():

            parts = line.split(
                ":",
                1
            )

            if len(parts) == 2:

                score = parts[1].strip()

            break


    # --------------------------------------------------------
    # BOX
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
    # CELÝ POSUDEK
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
