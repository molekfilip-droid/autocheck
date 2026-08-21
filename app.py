import streamlit as st
import json
import requests

st.set_page_config(page_title="AutoCheck CZ", page_icon="🚗", layout="wide")

st.title("🚗 AutoCheck CZ – Expertní analýza ojetiny")
st.subheader("Hloubkový technický posudek, skrytá rizika a nákupní verdikt")

default_key = st.secrets.get("GROQ_API_KEY", "")

st.sidebar.markdown("### Nastavení")
api_key = st.sidebar.text_input("Groq API Key", value=default_key, type="password").strip()

st.markdown("### 📋 Automatické vyplnění z inzerátu")
ad_text_input = st.text_area("Zkopíruj text inzerátu (popis, výbavu, parametry)...", placeholder="Sem vlož inzerát z Bazoše, Sauta apod...")

if "form_model" not in st.session_state:
    st.session_state.form_model = ""
    st.session_state.form_year = 2020
    st.session_state.form_km = 0
    st.session_state.form_price = 0
    st.session_state.form_fuel = "Benzín"
    st.session_state.form_gearbox = "Manuální"
    st.session_state.parsed_equipment = "Zatím neuloženo – vlož inzerát a klikni na tlačítko výše."

def call_groq(prompt_text, max_tokens=3000):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.3,
        "max_tokens": max_tokens
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")
    return response.json()["choices"][0]["message"]["content"].strip()

if st.button("✨ Načíst data z textu inzerátu"):
    if not api_key:
        st.error("Chybí Groq API klíč v secrets nebo v sidebaru.")
    elif not ad_text_input.strip():
        st.warning("Vlož nejdřív text inzerátu.")
    else:
        with st.spinner("AI parsuje inzerát a detekuje výbavu..."):
            try:
                p_text = f"""Jsi parser inzerátů. Z textu vrať POUZE validní JSON (bez ```json). Vše v češtině!
Text: "{ad_text_input}"
Struktura JSON:
{{
    "model": "značka a model",
    "year": rok výroby číslo,
    "km": nájezd číslo,
    "price": cena číslo,
    "fuel": "Benzín" nebo "Nafta" nebo "Hybrid" nebo "Elektro",
    "gearbox": "Manuální" nebo "Automatická",
    "equipment_summary": "Stručný přehled výbavy"
}}"""
                res = call_groq(p_text, 500)
                if res.startswith("```json"): res = res[7:]
                if res.endswith("```"): res = res[:-3]
                
                data = json.loads(res.strip())
                st.session_state.form_model = data.get("model", "")
                st.session_state.form_year = int(data.get("year", 2020))
                st.session_state.form_km = int(data.get("km", 0))
                st.session_state.form_price = int(data.get("price", 0))
                st.session_state.form_fuel = data.get("fuel", "Benzín")
                st.session_state.form_gearbox = data.get("gearbox", "Manuální")
                st.session_state.parsed_equipment = data.get("equipment_summary", "Bez popisu výbavy.")
                st.success("Údaje a výbava úspěšně načteny!")
            except Exception as e:
                st.error(f"Chyba při parsování: {e}")

st.markdown("---")
with st.expander("
