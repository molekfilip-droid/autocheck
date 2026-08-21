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

if "form_model" not in st.session_state:
    st.session_state.form_model = "Škoda Octavia 1.5 TSI"
    st.session_state.form_year = 2021
    st.session_state.form_km = 118000
    st.session_state.form_price = 399000
    st.session_state.form_fuel = "Benzín"
    st.session_state.form_gearbox = "Manuální"

def call_groq(prompt_text, max_tokens=2500):
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
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=20)
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
        with st.spinner("AI parsuje inzerát..."):
            try:
                parse_prompt = f"""
                Jsi parser inzerátů ojetých aut. Z následujícího textu inzerátu vytáhni údaje a vrať POUZE validní JSON (bez markdownu ```json). 
                DŮLEŽITÉ: Všechny textové hodnoty musí být výhradně v češtině!
                Text inzerátu: "{ad_text_input}"
                
                Struktura JSON:
                {{
                    "model": "přesná značka a model auta",
                    "year": rok výroby jako celé číslo,
                    "km": nájezd v km jako celé číslo,
                    "price": cena v Kč jako celé číslo,
                    "fuel": "Benzín" nebo "Nafta" nebo "Hybrid" nebo "Elektro",
                    "gearbox": "Manuální" nebo "Automatická"
                }}
                """
                res_text = call_groq(parse_prompt, max_tokens=300)
                if res_text.startswith("```json"): res_text = res_text[7:]
                if res_text.endswith("```"): res_text = res_text[:-3]
                
                parsed_data = json.loads(res_text.strip())
                
                st.session_state.form_model = parsed_data.get("model", st.session_state.form_model)
                st.session_state.form_year = int(parsed_data.get("year", st.session_state.form_year))
                st.session_state.form_km = int(parsed_data.get("km", st.session_state.form_km))
                st.session_state.form_price = int(parsed_data.get("price", st.session_state.form_price))
                st.session_state.form_fuel = parsed_data.get("fuel", st.session_state.form_fuel)
                st.session_state.form_gearbox = parsed_data.get("gearbox", st.session_state.form_gearbox)
                
                st.success("Údaje úspěšně doplněny do formuláře!")
            except Exception as e:
                st.error(f"Chyba při parsování: {e}")

st.markdown("---")

# --- FORMULÁŘ ---
with st.form("car_form"):
    st.markdown("### 🚗 Parametry vozidla")
    col1, col2 = st.columns(2)
    model = col1.text_input("Značka a model", value=st.session_state.form_model)
    year = col2.number_input("Rok výroby", min_value=1990, max_value=2026, value=st.session_state.form_year)
    
    km = col1.number_input("Nájezd (km)", min_value=0, value=st.session_state.form_km)
    price = col2.number_input("Cena (Kč)", min_value=0, value=st.session_state.form_price)
    
    fuel_options = ["Benzín", "Nafta", "Hybrid", "Elektro"]
    default_fuel_idx = fuel_options.index(st.session_state.form_fuel) if st.session_state.form_fuel in fuel_options else 0
    fuel = st.selectbox("Palivo", fuel_options, index=default_fuel_idx)
    
    gearbox_options = ["Manuální", "Automatická"]
    default_gear_idx = gearbox_options.index(st.session_state.form_gearbox) if st.session_state.form_gearbox in gearbox_options else 0
    gearbox = st.selectbox("Převodovka", gearbox_options, index=default_gear_idx)
    
    submitted = st.form_submit_button("🚀 Spustit hloubkovou expertní analýzu")

if submitted:
    if not api_key:
        st.error("Chybí Groq API klíč.")
    else:
        with st.spinner('Špičkový mechanik a auditor prověřuje motor, převodovku, trh a rizika...'):
            try:
                prompt = f"""
                Jsi hlavní šéfmechanik, soudní znalec a expert na trh ojetých vozů v ČR s 25 lety praxe. 
                Proveď maximálně detailní, nekompromisní a hloubkovou analýzu tohoto vozidla:
                - Model: {model}
                - Rok výroby: {year}
                - Nájezd: {km} km
                - Cena: {price} Kč
                - Palivo: {fuel}
                - Převodovka: {gearbox}

                ABSOLUTNÍ PRAVIDLO: Celá odpověď včetně všech popisů, hodnocení a položek musí být psaná 100% plynulou
