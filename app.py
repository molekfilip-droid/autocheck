import streamlit as st
import json
import requests

# Nastavení stránky
st.set_page_config(page_title="AutoCheck CZ - Pro AI analýza", page_icon="🚗", layout="wide")

st.title("🚗 AutoCheck CZ – Expertní analýza ojetiny")
st.subheader("Hloubkový technický posudek, skrytá rizika a nákupní verdikt")

# Automatické načtení klíče ze Streamlit secrets
default_key = st.secrets.get("GROQ_API_KEY", "")

st.sidebar.markdown("### Nastavení")
api_key = st.sidebar.text_input(
    "Groq API Key", 
    value=default_key, 
    type="password"
).strip()

# --- SEKCE PRO NAČTENÍ Z TEXTU INZERÁTU ---
st.markdown("### 📋 Automatické vyplnění z inzerátu")
ad_text_input = st.text_area("Zkopíruj text inzerátu (popis, výbavu, parametry)...", placeholder="Sem vlož inzerát z Bazoše, Sauta apod...")

# Inicializace session state
if "form_model" not in st.session_state:
    st.session_state.form_model = ""
    st.session_state.form_year = 2020
    st.session_state.form_km = 0
    st.session_state.form_price = 0
    st.session_state.form_fuel = "Benzín"
    st.session_state.form_gearbox = "Manuální"
    st.session_state.parsed_equipment = "Zatím neuloženo – vlož inzerát a klikni na tlačítko výše."

def call_groq(prompt_text, max_tokens=3000):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.3,
        "max_tokens": max_tokens
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")
    res_json = response.json()
    return res_json["choices"][0]["message"]["content"].strip()

if st.button("✨ Načíst data z textu inzerátu"):
    if not api_key:
        st.error("Chybí Groq API klíč v secrets nebo v sidebaru.")
    elif not ad_text_input.strip():
        st.warning("Vlož nejdřív text inzerátu.")
    else:
        with st.spinner("AI parsuje inzerát a detekuje výbavu..."):
            try:
                parse_prompt = """
                Jsi parser inzerátů ojetých aut. Z následujícího textu inzerátu vytáhni údaje a vrať POUZE validní JSON (bez markdownu ```json). 
                DŮLEŽITÉ: Všechny textové hodnoty musí být výhradně v češtině!
                Text inzerátu: "{ad_text}"
                
                Struktura JSON:
                {{
                    "model": "přesná značka a model auta",
                    "year": rok výroby jako celé číslo,
                    "km": nájezd v km jako celé číslo,
                    "price": cena v Kč jako celé číslo,
                    "fuel": "Benzín" nebo "Nafta" nebo "Hybrid" nebo "Elektro",
                    "gearbox": "Manuální" nebo "Automatická",
                    "equipment_summary": "Stručný přehled nejdůležitější výbavy a stavu zjištěného z inzerátu (např. navigace, kůže, tažné zařízení, po servisu...)"
                }}
                """.format(ad_text=ad_text_input)
                
                res_text = call_groq(parse_prompt, max_tokens=500)
                if res_text.startswith("```json"): res_text = res_text[7:]
                if res_text.endswith("```"): res_text = res_text[:-3]
                
                parsed_data = json.loads(res_text.strip())
                
                st.session_state.form_model = parsed_data.get("model", st.session_state.form_model)
                st.session_state.form_year = int(parsed_data.get("year", 2020))
                st.session_state.form_km = int(parsed_data.get("km", 0))
                st.session_state.form_price = int(parsed_data.get("price", 0))
                st.session_state.form_fuel = parsed_data.get("fuel", "Benzín")
                st.session_state.form_gearbox = parsed_data.get("gearbox", "Manuální")
                st.session_state.parsed_equipment = parsed_data.get("equipment_summary", "Výbava nebyla specificky detekována.")
                
                st.success("Údaje a výbava úspěšně načteny!")
            except Exception as e:
                st.error(f"Chyba při parsování: {e}")

st.markdown("---")

# Zobrazení toho, co AI z inzerátu vytáhla stran výbavy
with st.expander("🔍 Zkontrolov
