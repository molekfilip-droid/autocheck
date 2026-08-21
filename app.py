import streamlit as st
import requests
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
    st.session_state.parsed_equipment = "Zatím neuloženo – vlož inzerát a klikni na tlačítko výše."

def call_groq(prompt_text, max_tokens=1000):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.2,
        "max_tokens": max_tokens
    }
    
    time.sleep(2)
    
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=45)
    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")
    return response.json()["choices"][0]["message"]["content"].strip()

if st.button("✨ Načíst data z textu inzerátu"):
    if not api_key:
        st.error("Chybí Groq API klíč v secrets nebo v sidebaru.")
    elif not ad_text_input.strip():
        st.warning("Vlož nejdřív text inzerátu.")
    else:
        with st.spinner("AI vytahuje parametry a výbavu v češtině..."):
            try:
                clean_ad = ad_text_input.replace('"', "'").replace('\n', ' ').replace('\r', ' ')
                p_text = f"""Z následujícího inzerátu vyextrahuj parametry a vrať PŘESNĚ v tomto formátu odděleném středníky (žádný jiný text):
model|rok|km|cena|palivo|prevodovka|vybava
Například: Škoda Octavia|2019|150000|350000|Nafta|Manuální|Vyhřívané sedačky, navigace
Text inzerátu: "{clean_ad}"
"""
                res = call_groq(p_text, 200)
                parts = res.split('|')
                if len(parts) >= 6:
                    st.session_state.form_model = parts[0].strip()
                    st.session_state.form_year = int(re.sub(r'\D', '', parts[1]) or 2020)
                    st.session_state.form_km = int(re.sub(r'\D', '', parts[2]) or 0)
                    st.session_state.form_price = int(re.sub(r'\D', '', parts[3]) or 0)
                    
                    f_val = parts[4].strip()
                    st.session_state.form_fuel = f_val if f_val in ["Benzín", "Nafta", "Hybrid", "Elektro"] else "Benzín"
                    
                    g_val = parts[5].strip()
                    st.session_state.form_gearbox = g_val if g_val in ["Manuální", "Automatická"] else "Manuální"
                    
                    if len(parts) > 6:
                        st.session_state.parsed_equipment = parts[6].strip()
                    st.success("Data úspěšně načtena!")
                else:
                    raise Exception("Nepodařilo se správně parsovat odpovídající řetězec.")
            except Exception as e:
                st.session_state.parsed_equipment = ad_text_input
                st.warning(f"Pozor: Automatické vyplnění selhalo ({e}), text inzerátu byl uložen do výbavy.")

st.markdown("---")

with st.expander("🔍 Zkontrolovat načtenou výbavu (Detailní přehled)", expanded=True):
    st.info(st.session_state.parsed_equipment)

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
        with st.spinner("Prohledávám trh a generuji posudek..."):
            try:
                search_query = f"{model} {year} cena ojetiny bazar"
                search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(search_query)}"
                headers_ddg = {"User-Agent": "Mozilla/5.0"}
                web_snippets = ""
                
                try:
                    resp_ddg = requests.get(search_url, headers=headers_ddg, timeout=10)
                    if resp_ddg.status_code == 200:
                        snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', resp_ddg.text, re.DOTALL)
                        clean_snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:2]]
                        web_snippets = " ".join(clean_snippets)
                except Exception:
                    web_snippets = "Tržní data nedostupná."

                extracted_equipment_desc = st.session_state.parsed_equipment
                
                main_prompt = f"""Jsi špičkový český automobilový expert na ojetá auta. Vypracuj kompletní expertní posudek v češtině.

Hodnocené vozidlo:
- Model: {model}
- Rok výroby: {year}
- Nájezd: {km} km
- Inzerovaná cena: {price} Kč
- Palivo: {fuel} | Převodovka: {gearbox}
- Výbava: {extracted_equipment_desc}
- Tržní kontext: {web_snippets}

Dodrž tuto přesnou strukturu pomocí Markdown nadpisů:

## VERDIKT: [Zvol jedno: KUPUJ / FÉROVÁ NABÍDKA nebo ZVÁŽIT / JEDNAT O CENU nebo RUCE PRYČ / PŘEDRAŽENO]
**Shrnutí:** [Jedna věta shrnutí]

### 💰 Tržní hodnocení ceny a férové rozpětí
[Zde zhodnoť cenu, odhadni férové cenové rozpětí a napiš odhadovaný servis na 2 roky]

### ⚙️ Technický stav: Motor a převodovka
[Rozbor motoru, převodovky a spolehlivosti]

### ⚠️ Typické slabiny a rizika
* [Slabina 1]
* [Slabina 2]
* [Slabina 3]

### 🔍 Inspekční checklist při prohlídce
* [Na co se zaměřit 1]
* [Na co se zaměřit 2]
* [Na co se zaměřit 3]

### 🏁 Doporučení a nákupní taktika
[Závěrečné doporučení a jak případně smlouvat]
"""

                analysis_result = call_groq(main_prompt, 1200)
                
                st.markdown("---")
                st.markdown(analysis_result)
                
            except Exception as e:
                st.error(f"Chyba při generování analýzy: {e}")
