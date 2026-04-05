import streamlit as st
import requests
import pandas as pd

# --- CONFIGURATION ---
API_KEY = st.secrets["api_key"]

st.set_page_config(page_title="Scanner Multi-Sports 2-Issues", layout="wide")

st.title("🎯 Scanner Expert : Sports à 2 Issues (Sans Nul)")
st.sidebar.header("⚙️ Paramètres")
mise_totale_cible = st.sidebar.number_input("Budget total (€)", value=100)
arrondi = st.sidebar.selectbox("Arrondir les mises à :", [1, 2, 5, 10], index=2) 

# Liste des 3 bookmakers ARJEL
BOOKIES_CIBLES = ['winamax', 'unibet_fr', 'betclic_fr']

# Liste des sports à 2 issues (keys officielles de l'API)
SPORTS_KEYS = [
    'tennis_atp', 'tennis_wta', 'basketball_nba', 'basketball_euroleague', 
    'mma_mixed_martial_arts', 'icehockey_nhl', 'volleyball_world_championship',
    'table_tennis_ittf'
]

if st.button('🚀 Scanner tous les sports (Tennis, Basket, MMA, etc.)'):
    with st.spinner('Analyse des opportunités 2-ways...'):
        results = []
        
        # On boucle sur chaque sport pour être sûr de ne rien rater
        for sport in SPORTS_KEYS:
            url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={API_KEY}&regions=eu&markets=h2h'
            
            try:
                response = requests.get(url)
                if response.status_code != 200: continue
                data = response.json()

                for match in data:
                    cotes = {}
                    for b in match.get('bookmakers', []):
                        if b['key'] in BOOKIES_CIBLES:
                            market = b['markets'][0]
                            outcomes = market['outcomes']
                            
                            # SÉCURITÉ ABSOLUE : Uniquement si 2 issues exactement
                            if len(outcomes) == 2:
                                cotes[b['title']] = {o['name']: o['price'] for o in outcomes}

                    noms_bk = list(cotes.keys())
                    if len(noms_bk) >= 2:
                        for i in range(len(noms_bk)):
                            for j in range(i + 1, len(noms_bk)):
                                bk1, bk2 = noms_bk[i], noms_bk[j]
                                eqs = list(cotes[bk1].keys())
                                if len(eqs) < 2: continue
                                
                                # Test des deux combinaisons (Vainqueur 1 vs Vainqueur 2)
                                for v1, v2, n1, n2, b1, b2 in [
                                    (cotes[bk1][eqs[0]], cotes[bk2][eqs[1]], eqs[0], eqs[1], bk1, bk2),
                                    (cotes[bk1][eqs[1]], cotes[bk2][eqs[0]], eqs[1], eqs[0], bk1, bk2)
                                ]:
                                    rendement = (1/v1) + (1/v2)
                                    
                                    if rendement < 0.999:
                                        m1_raw = (1/v1 / rendement) * mise_totale_cible
                                        m1 = max(arrondi, round(m1_raw / arrondi) * arrondi)
                                        m2_raw = (m1 * v1) / v2
                                        m2 = max(arrondi, round(m2_raw / arrondi) * arrondi)
                                        
                                        total = m1 + m2
                                        gain = min((m1 * v1) - total, (m2 * v2) - total)
                                        perc = (gain / total) * 100

                                        if gain > -0.2:
                                            # Gestion des Emojis selon le sport
                                            title = match['sport_title']
                                            emoji = "🎾" if "Tennis" in title else "🏀" if "Basket" in title else "🏒" if "Hockey" in title else "🥊" if "MMA" in title else "🏐" if "Volley" in title else "🏓" if "Table" in title else "🎯"
                                            
                                            results.append({
                                                'Sport': f"{emoji} {title}",
                                                'Match': f"{eqs[0]} vs {eqs[1]}",
                                                'Profit %': f"{round(perc, 2)}%",
                                                'Pari 1': f"{int(m1)}€ sur {b1} ({n1} @{v1})",
                                                'Pari 2': f"{int(m2)}€ sur {b2} ({n2} @{v2})",
                                                'Gain Net': f"{round(gain, 2)}€",
                                                'Total': f"{int(total)}€"
                                            })
            except: continue

        if results:
            st.success(f"✅ {len(results)} Surebets détectés sur les sports à 2 issues !")
            df = pd.DataFrame(results).sort_values(by='Profit %', ascending=False)
            st.table(df)
        else:
            st.info("Aucun décalage majeur trouvé pour le moment. Réessaie d'ici 15-30 minutes !")

st.sidebar.markdown("---")
st.sidebar.warning("💡 **Important Hockey :** Vérifie que le pari est bien 'Vainqueur Final' (Prolongations incluses) sur les deux sites.")
