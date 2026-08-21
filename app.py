import streamlit as st
import requests
import re
import time
import pandas as pd
import json

st.set_page_config(page_title="AutoCheck CZ", page_icon="🚗", layout="wide")

st.title("🚗 AutoCheck CZ – Expertní analýza ojetiny")
st.subheader("Hloubkový technický posudek, reálná tržní data a nákupní verdikt")

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
    st.session_state.parsed_equipment = "Zatím neuloženo."

def call_groq(prompt_text, max_tokens=2500):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.1,
        "max_tokens": max_tokens
    }
    time.sleep(1)
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")
    return response.json()["choices"][0]["message"]["content"].strip()

if st.button("✨ Načíst data z textu inzerátu"):
    if not api_key:
        st.error("Chybí Groq API klíč.")
    elif not ad_text_input.strip():
        st.warning("Vlož nejdřív text inzerátu.")
    else:
        with st.spinner("AI parsuje data..."):
            try:
                p_text = f"""Jsi extraktor dat. Z inzerátu vytáhni parametry a vrať POUZE validní JSON v tomto formátu:
{{
  "model": "značka a model",
  "rok": 2020,
  "km": 150000,
  "cena": 300000,
  "palivo": "Benzín",
  "prevodovka": "Manuální",
  "vybava": "seznam výbavy"
}}
Text inzerátu: "{ad_text_input.replace('"', "'")}"
"""
                res = call_groq(p_text, 500)
                # Očistíme výstup od markdown bloků
                res = re.sub(r'```json|```', '', res).strip()
                data = json.loads(res)
                
                st.session_state.form_model = data.get("model", "")
                st.session_state.form_year = int(data.get("rok", 2020))
                st.session_state.form_km = int(data.get("km", 0))
                st.session_state.form_price = int(data.get("cena", 0))
                st.session_state.form_fuel = data.get("palivo", "Benzín")
                st.session_state.form_gearbox = data.get("prevodovka", "Manuální")
                st.session_state.parsed_equipment = data.get("vybava", "Nespecifikováno")
                st.success("Data načtena!")
            except Exception as e:
                st.session_state.parsed_equipment = ad_text_input
                st.error(f"Automatika selhala, použil jsem surový text. Chyba: {e}")

st.markdown("---")
st.markdown("### 🔍 Přehled parametrů a výbavy")
col_t1, col_t2 = st.columns(2)
with col_t1:
    df_params = pd.DataFrame([
        {"Parametr": "Model", "Hodnota": st.session_state.form_model},
        {"Parametr": "Rok", "Hodnota": st.session_state.form_year},
        {"Parametr": "Nájezd", "Hodnota": f"{st.session_state.form_km:,} km"},
        {"Parametr": "Cena", "Hodnota": f"{st.session_state.form_price:,} Kč"}
    ])
    st.table(df_params)
with col_t2:
    st.write("**Výbava:**")
    st.info(st.session_state.parsed_equipment)

st.markdown("---")
with st.form("car_form"):
    st.markdown("### ⚙️ Úprava před analýzou")
    model = st.text_input("Značka a model", value=st.session_state.form_model)
    col1, col2 = st.columns(2)
    year = col1.number_input("Rok výroby", value=st.session_state.form_year)
    km = col2.number_input("Nájezd (km)", value=st.session_state.form_km)
    price = col1.number_input("Cena (Kč)", value=st.session_state.form_price)
    fuel = col2.selectbox("Palivo", ["Benzín", "Nafta", "Hybrid", "Elektro"], index=["Benzín", "Nafta", "Hybrid", "Elektro"].index(st.session_state.form_fuel) if st.session_state.form_fuel in ["Benzín", "Nafta", "Hybrid", "Elektro"] else 0)
    submitted = st.form_submit_button("🚀 Spustit expertní analýzu")

if submitted:
    with st.spinner("Generuji expertní posudek..."):
        prompt = f"""Jsi automobilový expert. Napiš detailní posudek pro: {model}, rok {year}, nájezd {km}km, cena {price}Kč.
        Výbava: {st.session_state.parsed_equipment}
        Struktura:
        ## VERDIKT
        ### 💰 Tržní hodnocení ceny
        ### ⚙️ Technický stav (motor/převodovka)
        ### ⚠️ Typické slabiny
        ### 🔍 Checklist při prohlídce
        ### 🏁 Závěrečné doporučení"""
        try:
            result = call_groq(prompt)
            st.markdown(result)
        except Exception as e:
            st.error(f"Chyba: {e}")
