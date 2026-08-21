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
                Jsi parser inzerátů ojetých aut. Z následujícího textu inzerátu vytáhni údaje a vrať POUZE validní JSON (bez markdownu ```json):
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

                Vrať odpověď POUZE jako validní JSON objekt s touto přesnou strukturou (bez markdownu ```json):
                {{
                    "verdict": "🟢 KUPUJ / VÝBORNÁ NABÍDKA" nebo "🟡 ZVÁŽIT RIZIKA / MÍRNĚ PŘEDRAŽENO" nebo "🔴 RUCE PRYČ / VELKÉ RIZIKO",
                    "verdict_summary": "1-2 věty ostrého shrnutí, proč tento verdikt",
                    "fair_price_min": minimální férová trhová cena v Kč (číslo),
                    "fair_price_max": maximální férová trhová cena v Kč (číslo),
                    "price_evaluation": "Podrobný rozbor ceny vzhledem k aktuálnímu trhu v ČR, nájezdu a roku výroby",
                    "engine_gearbox_analysis": "Detailní technický rozbor motoru a převodovky pro tento konkrétní model (typické slabiny, na co trpí, životnost rozvodů, vstřikovačů, turba nebo spojky/automatu)",
                    "common_failures": [
                        "Specifická závada/bolístka tohoto modelu 1",
                        "Specifická závada/bolístka tohoto modelu 2",
                        "Specifická závada/bolístka tohoto modelu 3"
                    ],
                    "servicing_cost_2years": "Realistický odhad nutných investic a servisu na následující 2 roky (včetně rozpisů částek v Kč)",
                    "inspection_checklist": [
                        "Konkrétní věc k prověření na zvedáku nebo diagnostice 1",
                        "Konkrétní věc k prověření na zvedáku nebo diagnostice 2",
                        "Konkrétní věc k prověření na zvedáku nebo diagnostice 3",
                        "Konkrétní věc k prověření na zvedáku nebo diagnostice 4"
                    ],
                    "recommendation": "Závěrečné doporučení, jak se k nákupu postavit, na co ukázat při smlouvání o ceně a zda auto brát či nebrat."
                }}
                """
                
                result_text = call_groq(prompt, max_tokens=2500)
                if result_text.startswith("```json"):
                    result_text = result_text[7:]
                if result_text.endswith("```"):
                    result_text = result_text[:-3]
                    
                data = json.loads(result_text.strip())
                
                # Vykreslení výsledků do přehledného UI
                st.markdown("---")
                st.header(f"Výsledek auditu: {data['verdict']}")
                st.info(data['verdict_summary'])
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Odhadovaná férová cena", f"{data['fair_price_min']:,} - {data['fair_price_max']:,} Kč".replace(",", " "))
                with col_b:
                    st.metric("Odhadovaný servis na 2 roky", data['servicing_cost_2years'])
                
                st.markdown("### 💰 Tržní hodnocení ceny")
                st.write(data['price_evaluation'])
                
                st.markdown("### ⚙️ Technický stav: Motor a převodovka")
                st.write(data['engine_gearbox_analysis'])
                
                st.markdown("### ⚠️ Typické slabiny a rizika tohoto modelu")
                for failure in data['common_failures']:
                    st.error(f"• {failure}")
                    
                st.markdown("### 🔍 Inspekční checklist (Na co se 100% podívat)")
                for check in data['inspection_checklist']:
                    st.warning(f"✓ {check}")
                    
                st.markdown("### 🏁 Závěrečný verdikt a doporučení")
                st.success(data['recommendation'])
                
            except Exception as e:
                st.error(f"Chyba při generování hloubkové analýzy: {e}")
