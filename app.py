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


# Aktuální Gemini model
MODEL = "gemini-3-flash-preview"


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
# SESSION STATE
# ============================================================

if "analysis" not in st.session_state:
    st.session_state.analysis = None


# ============================================================
# API KEY
# ============================================================

def get_api_key():

    # Nejprve zkusíme Streamlit secrets
    try:
        secret = st.secrets.get(
            "GEMINI_API_KEY",
            ""
        )
    except Exception:
        secret = ""

    if secret:
        return secret.strip()

    # Jinak vezmeme klíč ze sidebaru
    return st.session_state.get(
        "manual_api_key",
        ""
    ).strip()


# ============================================================
# GEMINI
# ============================================================

def gemini_call(prompt):

    api_key = get_api_key()

    if not api_key:
        raise Exception(
            "Chybí Gemini API Key."
        )

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

                system_instruction=(
                    "Jsi zkušený český expert "
                    "na ojeté automobily. "
                    "Odpovídej vždy česky, "
                    "prakticky a konkrétně."
                )
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

    if text:

        return text.strip()


    # ========================================================
    # DIAGNOSTIKA PRÁZDNÉ ODPOVĚDI
    # ========================================================

    details = []

    try:

        details.append(
            f"Response: {response}"
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
Analyzuj následující inzerát ojetého automobilu.

TEXT INZERÁTU:

{ad_text}

Jsi odborník na nákup ojetých aut v České republice.

Cílem je poradit kupujícímu,
zda má smysl toto konkrétní auto koupit.

DŮLEŽITÁ PRAVIDLA:

- Nevymýšlej údaje, které nejsou v inzerátu.
- Pokud údaj není uvedený, napiš "neuvedeno".
- Rozlišuj mezi tím, co tvrdí prodejce,
  a tím, co lze považovat za ověřenou skutečnost.
- U typických závad modelu jasně napiš,
  že jde o typické riziko, nikoliv potvrzenou závadu.
- Buď realistický.
- Nehádej přesnou historii auta.
- Zaměř se na praktické rozhodnutí kupujícího.

Použij následující strukturu:

# 🚗 VERDIKT

Vyber pouze jednu možnost:

KUPUJ

VYJEDNÁVAT

RUCE PRYČ

# ⭐ SKÓRE

Hodnocení od 1 do 10.

# 🚘 IDENTIFIKACE AUTA

Značka:
Model:
Rok:
Motor:
Výkon:
Palivo:
Převodovka:
Pohon:
Karoserie:
Nájezd:
Cena:

# 🛡️ VÝBAVA

Vypiš nejdůležitější výbavu
uvedenou v inzerátu.

# 💰 CENA

Uveď:

Férová cena:
Doporučená maximální cena:
Cena pro zahájení vyjednávání:

Potom vysvětli,
proč považuješ cenu za dobrou,
průměrnou nebo vysokou.

Pokud nemáš dost informací
pro přesné určení ceny,
výslovně to napiš.

# ⚙️ TECHNIKA

Zhodnoť:

- motor
- převodovku
- pohon
- spolehlivost
- očekávané problémy

Zaměř se na konkrétní motorizaci,
pokud ji lze z inzerátu určit.

# ⚠️ NEJVĚTŠÍ RIZIKA

Uveď 5 až 8 nejdůležitějších rizik.

U každého napiš:

RIZIKO:
JAK SE PROJEVUJE:
JAK HO OVĚŘIT:

# 🔍 CHECKLIST PROHLÍDKY

Napiš 10 konkrétních věcí,
které má kupující před koupí zkontrolovat.

Zahrň například:

- studený start
- motor
- převodovku
- podvozek
- brzdy
- karoserii
- pneumatiky
- elektroniku
- diagnostiku
- zkušební jízdu

Ale přizpůsob checklist konkrétnímu autu.

# 🔧 SERVIS

Odhadni potenciální servisní náklady
na následující 2 roky.

Uveď rozpětí v Kč.

Rozděl je na:

Běžný servis:
Možné opravy:
Rizikový scénář:

# 🤝 VYJEDNÁVÁNÍ

Napiš konkrétní argumenty,
které může kupující použít
ke snížení ceny.

# 🏁 ZÁVĚR

Napiš stručně:

- zda bys na auto jel
- co bys ověřil jako první
- jakou cenu bys považoval za dobrou
- za jakých podmínek bys auto koupil

Buď praktický a konkrétní.
"""


    return gemini_call(
        prompt
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "⚙️ AutoCheck CZ"
)


try:

    secret_key = st.secrets.get(
        "GEMINI_API_KEY",
        ""
    )

except Exception:

    secret_key = ""


api_key = st.sidebar.text_input(
    "Gemini API Key",
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
    "AI požadavků:"
)

st.sidebar.success(
    "1 request / analýza"
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
            "❌ Zadej Gemini API Key."
        )

    elif not ad_text.strip():

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


    # ========================================================
    # VERDIKT
    # ========================================================

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


    # ========================================================
    # SKÓRE
    # ========================================================

    score = "?"


    for line in result.splitlines():

        clean = line.strip().upper()


        if clean.startswith(
            "SKÓRE:"
        ):

            score = (
                line.split(
                    ":",
                    1
                )[1].strip()
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
    # CELÝ POSUDEK
    # ========================================================

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
