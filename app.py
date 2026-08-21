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
    clean_api_key = str(api_key).strip().strip("'").strip('"')
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {clean_api_key}", "Content-Type": "application/json"}
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
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")
    return response.json()["choices"][0]["message"]["content"].strip()

def call_groq_text(prompt_text, max_tokens=2500):
    clean_api_key = str(api_key).strip().strip("'").strip('"')
    url = "[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)"
    headers = {"Authorization": f"Bearer {clean_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.1,
        "max_tokens": max_tokens
    }
    time.sleep(1)
    response = requests.post(url, headers=headers, json=payload, timeout=60)
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
        st.markdown("#### 🚗 Základní parametry")
        df_params = pd.DataFrame([
            {"Parametr": "Model", "Hodnota": st.session_state.form_model},
            {"Parametr": "Rok výroby", "Hodnota": st.session_state.form_year},
            {"Parametr": "Nájezd", "Hodnota": f"{st.session_state.form_km:,} km"},
            {"Parametr": "Cena", "Hodnota": f"{st.session_state.form_price:,} Kč"},
            {"Parametr": "Palivo", "Hodnota": st.session_state.form_fuel},
            {"Parametr": "Převodovka", "Hodnota": st.session_state.form_gearbox}
        ])
        st.dataframe(df_params, use_container_width=True, hide_index=True)
        
    with col_t2:
        st.markdown("#### 🛡️ Extrahovaná výbava")
        df_eq = pd.DataFrame(eq_list)
        df_eq.columns = ["Kategorie", "Prvek výbavy"]
        st.dataframe(df_eq, use_container_width=True, hide_index=True)
else:
    st.info("Zatím nebyl načten žádný inzerát. Vlož text nahoře a klikni na tlačítko.")

st.markdown("---")

with st.form("car_form"):
    st.markdown("### ⚙️ Úprava parametrů před analýzou")
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
    
    submitted = st.form_submit_button("🚀 Spustit hloubkovou expertní analýzu")

if submitted:
    if not api_key:
        st.error("Chybí Groq API klíč.")
    elif not model.strip():
        st.warning("Zadej značku a model vozidla.")
    else:
        with st.spinner("Prohledávám trh a generuji hloubkový posudek..."):
            try:
                search_query = f"{model} {year} cena ojetiny bazar"
                search_url = f"[https://html.duckduckgo.com/html/?q=](https://html.duckduckgo.com/html/?q=){requests.utils.quote(search_query)}"
                headers_ddg = {"User-Agent": "Mozilla/5.0"}
                web_snippets = ""
                
                try:
                    resp_ddg = requests.get(search_url, headers=headers_ddg, timeout=10)
                    if resp_ddg.status_code == 200:
                        snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', resp_ddg.text, re.DOTALL)
                        clean_snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:3]]
                        web_snippets = " ".join(clean_snippets)
                except Exception:
                    web_snippets = "Tržní data nedostupná."

                eq_text = ", ".join([f"{x.get('kategorie')}: {x.get('prvek')}" for x in st.session_state.parsed_equipment if isinstance(x, dict)])
                
                main_prompt = f"""Jsi špičkový český automobilový expert na ojetá auta. Napiš PODROBNÝ, VYČERPÁVAJÍCÍ a KOMPLETNÍ expertní posudek v češtině.

Hodnocené vozidlo:
- Model: {model}
- Rok výroby: {year}
- Nájezd: {km} km
- Inzerovaná cena: {price} Kč
- Palivo: {fuel} | Převodovka: {gearbox}
- Výbava: {eq_text}
- Tržní kontext: {web_snippets}

Použij tuto přesnou strukturu nadpisů:

## VERDIKT: [Zvol jedno: KUPUJ / FÉROVÁ NABÍDKA nebo ZVÁŽIT / JEDNAT O CENU nebo RUCE PRYČ / PŘEDRAŽENO]
**Shrnutí:** [Podrobné shrnutí v 1-2 větách]

### 💰 Tržní hodnocení ceny a férové rozpětí
[Rozbor ceny, férové rozpětí v Kč, servisní náklady na 2 roky]

### ⚙️ Technický stav: Motor a převodovka
[Spolehlivost motoru, chování převodovky, specifická rizika]

### ⚠️ Typické slabiny a rizika
* [Slabina 1]
* [Slabina 2]
* [Slabina 3]

### 🔍 Inspekční checklist při prohlídce
* [Bod kontroly 1]
* [Bod kontroly 2]
* [Bod kontroly 3]

### 🏁 Doporučení a nákupní taktika
[Doporučení k diagnostice, tipy na smlouvání]
"""

                analysis_result = call_groq_text(main_prompt, 2500)
                st.markdown("---")
                st.markdown(analysis_result)
                
            except Exception as e:
                st.error(f"Chyba při generování analýzy: {e}")
