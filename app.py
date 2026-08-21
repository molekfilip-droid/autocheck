import streamlit as st
import requests
import json
import re
import time
import pandas as pd

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
    st.session_state.parsed_equipment = []
    st.session_state.raw_ad_loaded = False

def call_groq_json(prompt_text, max_tokens=1500):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [
            {"role": "system", "content": "Jsi přísný JSON extraktor. Vrať POUZE a JENOM validní JSON, bez jakéhokoliv dalšího textu, úvodu nebo závěru. Žádné markdown obálky typu ```json."},
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens
    }
    time.sleep(1)
    response = requests.post("[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)", headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")
    return response.json()["choices"][0]["message"]["content"].strip()

def call_groq_text(prompt_text, max_tokens=2500):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.1,
        "max_tokens": max_tokens
    }
    time.sleep(1)
    response = requests.post("[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)", headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")
    return response.json()["choices"][0]["message"]["content"].strip()

if st.button("✨ Načíst data z textu inzerátu"):
    if not api_key:
        st.error("Chybí Groq API klíč v secrets nebo v sidebaru.")
    elif not ad_text_input.strip():
        st.warning("Vlož nejdřív text inzerátu.")
    else:
        with st.spinner("AI parsuje parametry a výbavu..."):
            try:
                clean_ad = ad_text_input.replace('"', "'").replace('\n', ' ').replace('\r', ' ')
                p_text = f"""Z následujícího textu inzerátu vyextrahuj informace a vrať PŘESNĚ tento JSON formát (nic jiného):
{{
  "model": "Značka a model",
  "rok": 2020,
  "km": 150000,
  "cena": 300000,
  "palivo": "Benzín",
  "prevodovka": "Manuální",
  "vybava": [
    {{"kategorie": "Bezpečnost", "prvek": "ABS"}},
    {{"kategorie": "Komfort", "prvek": "Vyhřívaná sedadla"}}
  ]
}}

Pravidla:
- Palivo: "Benzín", "Nafta", "Hybrid" nebo "Elektro"
- Převodovka: "Manuální" nebo "Automatická"
- Vybava: Pole objektů rozdělené do kategorií (např. Bezpečnost, Komfort, Asistenti, Exteriér, Interiér).

Text inzerátu: "{clean_ad}"
"""
                res = call_groq_json(p_text, 1500)
                
                res_clean = re.sub(r'^```(?:json)?\s*', '', res, flags=re.IGNORECASE)
                res_clean = re.sub(r'\s*```$', '', res_clean)
                
                data = json.loads(res_clean.strip())
                
                st.session_state.form_model = data.get("model", "")
                st.session_state.form_year = int(data.get("rok", 2020))
                st.session_state.form_km = int(data.get("km", 0))
                st.session_state.form_price = int(data.get("cena", 0))
                
                f_val = data.get("palivo", "Benzín")
                st.session_state.form_fuel = f_val if f_val in ["Benzín", "Nafta", "Hybrid", "Elektro"] else "Benzín"
                
                g_val = data.get("prevodovka", "Manuální")
                st.session_state.form_gearbox = g_val if g_val in ["Manuální", "Automatická"] else "Manuální"
                
                st.session_state.parsed_equipment = data.get("vybava", [])
                st.session_state.raw_ad_loaded = True
                
                st.success("Data a výbava úspěšně načteny!")
            except Exception as e:
                st.session_state.parsed_equipment = [{"kategorie": "Celý text", "prvek": ad_text_input}]
                st.session_state.raw_ad_loaded = False
                st.warning(f"Pozor: Automatické parsování selhalo ({e}), text je k dispozici níže.")

st.markdown("---")

st.markdown("### 🔍 Přehled načtené výbavy a parametrů z inzerátu")
eq_list = st.session_state.parsed_equipment

if isinstance(eq_list, list) and len(eq_list) > 0 and isinstance(eq_list[0], dict) and st.session_state.raw_ad_loaded:
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
