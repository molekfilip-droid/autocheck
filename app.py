import streamlit as st
import requests
import json
import re
import time

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

def call_groq(prompt_text, max_tokens=2500):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "openai/gpt-oss-20b",
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
        st.error("Chybí Groq API klíč v secrets nebo v sidebaru.")
    elif not ad_text_input.strip():
        st.warning("Vlož nejdřív text inzerátu.")
    else:
        with st.spinner("AI parsuje parametry a výbavu..."):
            try:
                clean_ad = ad_text_input.replace('"', "'").replace('\n', ' ').replace('\r', ' ')
                p_text = f"""Jsi JSON extraktor inzerátů. Z následujícího textu vyextrahuj data a vrať PŘESNĚ a POUZE validní JSON objekt (bez markdown bloků jako ```json ... ```, jen čistý JSON) v tomto formátu:
{{
  "model": "Značka a model",
  "rok": 2020,
  "km": 150000,
  "cena": 300000,
  "palivo": "Nafta",
  "prevodovka": "Automatická",
  "vybava": ["ABS", "Navigace", "Vyhřívaná sedadla"]
}}

Pravidla:
- Palivo musí být přesně jedno z: "Benzín", "Nafta", "Hybrid", "Elektro"
- Převodovka musí být přesně jedna z: "Manuální", "Automatická"
- Vybava je pole (list) stringů jednotlivých prvků výbavy, vyházej marketingové kecy.

Text inzerátu: "{clean_ad}"
"""
                res = call_groq(p_text, 1200)
                # Ošetření pro případ, že by model přidal markdownové ohraničení
                res_clean = re.sub(r'^```json\s*|\s*```$', '', res, flags=re.DOTALL).strip()
                data = json.loads(res_clean)
                
                st.session_state.form_model = data.get("model", "")
                st.session_state.form_year = int(data.get("rok", 2020))
                st.session_state.form_km = int(data.get("km", 0))
                st.session_state.form_price = int(data.get("cena", 0))
                
                f_val = data.get("palivo", "Benzín")
                st.session_state.form_fuel = f_val if f_val in ["Benzín", "Nafta", "Hybrid", "Elektro"] else "Benzín"
                
                g_val = data.get("prevodovka", "Manuální")
                st.session_state.form_gearbox = g_val if g_val in ["Manuální", "Automatická"] else "Manuální"
                
                eq = data.get("vybava", [])
                st.session_state.parsed_equipment = [str(item).strip().capitalize() for item in eq if item]
                
                st.success("Data úspěšně načtena a strukturována!")
            except Exception as e:
                st.session_state.parsed_equipment = [ad_text_input]
                st.warning(f"Pozor: Parsování selhalo ({e}), uloženo jako text.")

st.markdown("---")

with st.expander("🔍 Zkontrolovat načtenou výbavu (Strukturovaný přehled)", expanded=True):
    eq_list = st.session_state.parsed_equipment
    if isinstance(eq_list, list) and len(eq_list) > 0:
        cols = st.columns(3)
        for i, item in enumerate(eq_list):
            cols[i % 3].markdown(f"✅ {item}")
    else:
        st.info("Zatím není načtená žádná výbava.")

with st.form("car_form"):
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
                search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(search_query)}"
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

                eq_text = ", ".join(st.session_state.parsed_equipment) if isinstance(st.session_state.parsed_equipment, list) else str(st.session_state.parsed_equipment)
                
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

                analysis_result = call_groq(main_prompt, 2500)
                st.markdown("---")
                st.markdown(analysis_result)
                
            except Exception as e:
                st.error(f"Chyba při generování analýzy: {e}")
