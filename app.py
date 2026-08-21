import streamlit as st
import json
import requests
import re

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
        "temperature": 0.2,
        "max_tokens": max_tokens
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=45)
    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")
    res_json = response.json()
    if "choices" not in res_json or len(res_json["choices"]) == 0:
        raise Exception("API vrátilo prázdnou odpověď.")
    return res_json["choices"][0]["message"]["content"].strip()

if st.button("✨ Načíst data z textu inzerátu"):
    if not api_key:
        st.error("Chybí Groq API klíč v secrets nebo v sidebaru.")
    elif not ad_text_input.strip():
        st.warning("Vlož nejdřív text inzerátu.")
    else:
        with st.spinner("AI parsuje inzerát a detekuje výbavu..."):
            try:
                clean_ad = ad_text_input.replace('"', "'").replace('\n', ' ')[:3000]
                p_text = f"""Jsi parser inzerátů ojetých vozů. Z následujícího textu extrahuj klíčové parametry a detailně shrň výbavu. Vrať POUZE platný JSON (bez markdown bloků ```json ... ```). Vše v češtině!
Text inzerátu: "{clean_ad}"

Struktura JSON:
{{
    "model": "přesná značka a model",
    "year": 2020,
    "km": 0,
    "price": 0,
    "fuel": "Benzín",
    "gearbox": "Manuální",
    "equipment_summary": "Kompletní detailní přehled prvků výbavy"
}}"""
                res = call_groq(p_text, 800)
                
                res = re.sub(r'^```json\s*', '', res, flags=re.IGNORECASE)
                res = re.sub(r'^```\s*', '', res)
                res = re.sub(r'\s*```$', '', res)
                
                match = re.search(r'\{.*\}', res, re.DOTALL)
                if match:
                    res = match.group(0)
                
                data = json.loads(res.strip())
                st.session_state.form_model = str(data.get("model", ""))
                st.session_state.form_year = int(data.get("year", 2020))
                st.session_state.form_km = int(data.get("km", 0))
                st.session_state.form_price = int(data.get("price", 0))
                
                f_val = str(data.get("fuel", "Benzín"))
                st.session_state.form_fuel = f_val if f_val in ["Benzín", "Nafta", "Hybrid", "Elektro"] else "Benzín"
                
                g_val = str(data.get("gearbox", "Manuální"))
                st.session_state.form_gearbox = g_val if g_val in ["Manuální", "Automatická"] else "Manuální"
                
                st.session_state.parsed_equipment = str(data.get("equipment_summary", "Bez popisu výbavy."))
                st.success("Údaje a výbava úspěšně načteny!")
            except Exception as e:
                st.error(f"Chyba při parsování: {e}")

st.markdown("---")

with st.expander("🔍 Zkontrolovat načtenou výbavu", expanded=True):
    st.info(st.session_state.parsed_equipment)

st.markdown("### 🚗 Parametry vozidla")
c1, c2 = st.columns(2)
model = c1.text_input("Značka a model", value=st.session_state.form_model)
year = c2.number_input("Rok výroby", min_value=1990, max_value=2026, value=st.session_state.form_year)
km = c1.number_input("Nájezd (km)", min_value=0, value=st.session_state.form_km, step=1000)
price = c2.number_input("Cena (Kč)", min_value=0, value=st.session_state.form_price, step=10000)

f_opts = ["Benzín", "Nafta", "Hybrid", "Elektro"]
f_idx = f_opts.index(st.session_state.form_fuel) if st.session_state.form_fuel in f_opts else 0
fuel = st.selectbox("Palivo", f_opts, index=f_idx)

g_opts = ["Manuální", "Automatická"]
g_idx = g_opts.index(st.session_state.form_gearbox) if st.session_state.form_gearbox in g_opts else 0
gearbox = st.selectbox("Převodovka", g_opts, index=g_idx)

submitted = st.button("🚀 Spustit hloubkovou expertní analýzu", type="primary")

if submitted:
    if not api_key:
        st.error("Chybí Groq API klíč.")
    elif not model.strip():
        st.warning("Zadej značku a model vozidla.")
    else:
        with st.spinner("Špičkový mechanik prověřuje techniku, reálnou výbavu a trh..."):
            try:
                clean_full_ad = ad_text_input.replace('"', "'").replace('\n', ' ')[:4000] if ad_text_input else "Neuveden"
                
                main_prompt = f"""Jsi přední český automobilový expert, mechanik a soudní znalec s 25 lety praxe. Proveď precizní, technicky bez
