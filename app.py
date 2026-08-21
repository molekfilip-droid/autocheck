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
                # Ošetření textu inzerátu proti rozbití JSON promptu
                clean_ad = ad_text_input.replace('"', "'").replace('\n', ' ')
                p_text = f"""Jsi parser inzerátů. Z následujícího textu vrať POUZE validní JSON. Žádný markdown, žádný text kolem. Vše v češtině!
Text inzerátu: "{clean_ad}"

Struktura JSON:
{{
    "model": "značka a model",
    "year": 2020,
    "km": 0,
    "price": 0,
    "fuel": "Benzín",
    "gearbox": "Manuální",
    "equipment_summary": "Stručný přehled výbavy"
}}"""
                res = call_groq(p_text, 600)
                
                # Vyčištění odpovědi od případných markdown bloků
                res = re.sub(r'^```json\s*', '', res, flags=re.IGNORECASE)
                res = re.sub(r'^```\s*', '', res, flags=re.IGNORECASE)
                res = re.sub(r'\s*```$', '', res)
                
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
                st.error(f"Chyba při parsování: {e}. Zkus text inzerátu vložit znovu nebo upravit.")

st.markdown("---")

with st.expander("🔍 Zkontrolovat načtenou výbavu", expanded=True):
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
        with st.spinner("Špičkový mechanik prověřuje motor, převodovku, výbavu a trh..."):
            try:
                clean_full_ad = ad_text_input.replace('"', "'").replace('\n', ' ') if ad_text_input else "Neuveden"
                main_prompt = f"""Jsi hlavní šéfmechanik a soudní znalec v ČR s 25 lety praxe. Proveď detailní analýzu.
Model: {model}, Rok: {year}, Nájezd: {km} km, Cena: {price} Kč, Palivo: {fuel}, Převodovka: {gearbox}
Celý inzerát: {clean_full_ad}

Pravidlo: Celá odpověď musí být 100% v češtině. Vrať POUZE validní JSON bez jakéhokoliv markdownu či komentářů:
{{
    "verdict": "🟢 KUPUJ / VÝBORNÁ NABÍDKA",
    "verdict_summary": "1-2 věty shrnutí",
    "fair_price_min": 100000,
    "fair_price_max": 150000,
    "price_evaluation": "Rozbor ceny vzhledem k trhu a výbavě",
    "engine_gearbox_analysis": "Technický rozbor motoru a převodovki",
    "common_failures": ["Bolístka 1", "Bolístka 2", "Bolístka 3"],
    "servicing_cost_2years": "Odhad servisu na 2 roky s částkami v Kč",
    "inspection_checklist": ["Kontrola 1", "Kontrola 2", "Kontrola 3", "Kontrola 4"],
    "recommendation": "Závěrečné doporučení pro vyjednávání"
}}"""
                res = call_groq(main_prompt, 4000)
                res = re.sub(r'^```json\s*', '', res, flags=re.IGNORECASE)
                res = re.sub(r'^```\s*', '', res, flags=re.IGNORECASE)
                res = re.sub(r'\s*```$', '', res)
                
                data = json.loads(res.strip())
                
                st.markdown("---")
                st.header(f"Výsledek auditu: {data['verdict']}")
                st.info(data['verdict_summary'])
                
                ca, cb = st.columns(2)
                with ca:
                    st.metric("Odhadovaná férová cena", f"{data['fair_price_min']:,} - {data['fair_price_max']:,} Kč".replace(",", " "))
                with cb:
                    st.markdown("**🔧 Odhadovaný servis na 2 roky:**")
                    st.success(data['servicing_cost_2years'])
                
                st.markdown("### 💰 Tržní hodnocení ceny")
                st.write(data['price_evaluation'])
                
                st.markdown("### ⚙️ Technický stav: Motor a převodovka")
                st.write(data['engine_gearbox_analysis'])
                
                st.markdown("### ⚠️ Typické slabiny a rizika")
                for f in data.get('common_failures', []):
                    st.error(f"• {f}")
                    
                st.markdown("### 🔍 Inspekční checklist")
                for chk in data.get('inspection_checklist', []):
                    st.warning(f"✓ {chk}")
                    
                st.markdown("### 🏁 Závěrečný verdikt")
                st.success(data['recommendation'])
                
            except Exception as e:
                st.error(f"Chyba při generování analýzy: {e}")
