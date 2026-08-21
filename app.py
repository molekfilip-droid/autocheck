if st.button("✨ Načíst data z textu inzerátu"):
    if not api_key:
        st.error("Chybí Groq API klíč v secrets nebo v sidebaru.")
    elif not ad_text_input.strip():
        st.warning("Vlož nejdřív text inzerátu.")
    else:
        with st.spinner("AI vytahuje parametry a výbavu v češtině..."):
            try:
                clean_ad = ad_text_input.replace('"', "'").replace('\n', ' ').replace('\r', ' ')
                p_text = f"""Jsi český asistent. Z následujícího inzerátu vyextrahuj parametry. POZOR: Položku "equipment_summary" napiš VÝHRADNĚ V ČEŠTINĚ jako přehledný souhrn výbavy z textu (žádná angličtina!).
Vrať PŘESNĚ tento JSON formát:
{{
    "model": "značka a model",
    "year": 2020,
    "km": 0,
    "price": 0,
    "fuel": "Benzín",
    "gearbox": "Manuální",
    "equipment_summary": "stručný přehled výbavy česky"
}}
Text: "{clean_ad}"
"""
                res = call_groq(p_text, 1000)
                res = re.sub(r'^```json\s*', '', res, flags=re.IGNORECASE)
                res = re.sub(r'^```\s*', '', res, flags=re.IGNORECASE)
                res = re.sub(r'\s*```$', '', res)
                
                match = re.search(r'\{.*\}', res, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                else:
                    raise Exception("Nenalezen validní JSON blok.")
                
                st.session_state.form_model = str(data.get("model", ""))
                st.session_state.form_year = int(data.get("year", 2020))
                st.session_state.form_km = int(data.get("km", 0))
                st.session_state.form_price = int(data.get("price", 0))
                
                f_val = str(data.get("fuel", "Benzín"))
                st.session_state.form_fuel = f_val if f_val in ["Benzín", "Nafta", "Hybrid", "Elektro"] else "Benzín"
                
                g_val = str(data.get("gearbox", "Manuální"))
                st.session_state.form_gearbox = g_val if g_val in ["Manuální", "Automatická"] else "Manuální"
                
                st.session_state.parsed_equipment = str(data.get("equipment_summary", "Bez popisu výbavy."))
                st.success("Data úspěšně načtena!")
            except Exception as e:
                st.session_state.parsed_equipment = ad_text_input
                st.warning(f"Pozor: Parsování narazilo na limit nebo problém ({e}), text byl zálohován.")

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
        with st.spinner("Prohledávám český trh a generuji posudek..."):
            try:
                time.sleep(2)
                
                search_query = f"{model} {year} cena ojetiny bazar"
                search_url = f"[https://html.duckduckgo.com/html/?q=](https://html.duckduckgo.com/html/?q=){requests.utils.quote(search_query)}"
                headers_ddg = {"User-Agent": "Mozilla/5.0"}
                web_snippets = ""
                
                try:
                    resp_ddg = requests.get(search_url, headers=headers_ddg, timeout=10)
                    if resp_ddg.status_code == 200:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(resp_ddg.text, 'html.parser')
                        results = []
                        for a in soup.find_all('a', class_='result__snippet', limit=4):
                            results.append(a.get_text())
                        web_snippets = " ".join(results)
                except Exception:
                    web_snippets = "Tržní data z webu nedostupná."

                clean_full_ad = ad_text_input.replace('"', "'").replace('\n', ' ') if ad_text_input else "Neuveden"
                extracted_equipment_desc = st.session_state.parsed_equipment
                
                main_prompt = f"""Jsi špičkový český automobilový expert na ojetá auta. Celá tvá odpověď, včetně všech popisků, hodnocení a položek, MUSÍ BÝT V ČEŠTINĚ.

Hodnocené vozidlo:
- Model: {model}
- Rok: {year}
- Nájezd: {km} km
- Inzerovaná cena: {price} Kč
- Palivo: {fuel} | Převodovka: {gearbox}
- Výbava: {extracted_equipment_desc}

Reálné tržní stopy z webu:
{web_snippets}

Instrukce:
1. Posudek piš střízlivě a reálně podle aktuální situace na českém trhu ojetin. Nevymýšlej si extrémní slevy, pokud je cena na trhu běžná. Respektuj reálnou hodnotu modelu.
2. Zohledni konkrétní výbavu a stav.
3. Nastav realistické rozpětí férové ceny (`fair_price_min` a `fair_price_max`).

Odpověz PŘESNĚ v tomto JSON formátu (vše v češtině):
{{
    "verdict": "🟢 KUPUJ / FÉROVÁ NABÍDKA nebo 🟡 ZVÁŽIT / JEDNAT O CENU nebo 🔴 RUCE PRYČ / PŘEDRAŽENO",
    "verdict_summary": "Shrnutí v jedné větě česky.",
    "fair_price_min": 450000,
    "fair_price_max": 490000,
    "price_evaluation": "Zhodnocení ceny s ohledem na výbavu a trh.",
    "engine_gearbox_analysis": "Rozbor motoru a převodovky.",
    "common_failures": [
        "Slabina 1",
        "Slabina 2",
        "Slabina 3"
    ],
    "servicing_cost_2years": "Odhad servisních nákladů na 2 roky v Kč.",
    "inspection_checklist": [
        "Kontrola 1",
        "Kontrola 2",
        "Kontrola 3"
    ],
    "recommendation": "Doporučení a taktika slevy."
}}"""

                res = call_groq(main_prompt, 2000)
                res = re.sub(r'^```json\s*', '', res, flags=re.IGNORECASE)
                res = re.sub(r'^```\s*', '', res, flags=re.IGNORECASE)
                res = re.sub(r'\s*```$', '', res)
                
                match_main = re.search(r'\{.*\}', res, res.DOTALL)
                if match_main:
                    data = json.loads(match_main.group(0))
                else:
                    raise Exception("Hlavní model nevrátil JSON blok.")
                
                st.markdown("---")
                st.header(f"Výsledek auditu: {data.get('verdict', 'Neznámý verdikt')}")
                st.info(data.get('verdict_summary', ''))
                
                ca, cb = st.columns(2)
                with ca:
                    p_min = data.get('fair_price_min', 0)
                    p_max = data.get('fair_price_max', 0)
                    st.metric("Odhadovaná férová cena", f"{p_min:,} - {p_max:,} Kč".replace(",", " "))
                with cb:
                    st.markdown("**🔧 Odhadovaný servis na 2 roky:**")
                    st.success(data.get('servicing_cost_2years', 'Neuvedeno'))
                
                st.markdown("### 💰 Tržní hodnocení ceny")
                st.write(data.get('price_evaluation', ''))
                
                st.markdown("### ⚙️ Technický stav: Motor a převodovka")
                st.write(data.get('engine_gearbox_analysis', ''))
                
                st.markdown("### ⚠️ Typické slabiny a rizika")
                for f in data.get('common_failures', []):
                    st.error(f"• {f}")
                    
                st.markdown("### 🔍 Inspekční checklist")
                for chk in data.get('inspection_checklist', []):
                    st.warning(f"✓ {chk}")
                    
                st.markdown("### 🏁 Závěrečný verdikt a doporučení")
                st.success(data.get('recommendation', ''))
                
            except Exception as e:
                st.error(f"Chyba při generování analýzy: {e}")
