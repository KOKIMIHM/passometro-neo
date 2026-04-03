import streamlit as st
import pandas as pd
from datetime import datetime
import json
import gspread
from google.oauth2.service_account import Credentials

# Configuração da página
st.set_page_config(page_title="Passômetro UTI Neo", layout="wide")

## --- INICIALIZANDO A MEMÓRIA DO APLICATIVO ---
if "form_leito" not in st.session_state: st.session_state.form_leito = ""
if "form_idade" not in st.session_state: st.session_state.form_idade = ""
if "form_vent" not in st.session_state: st.session_state.form_vent = ""
if "form_dados" not in st.session_state: st.session_state.form_dados = ""
if "form_prop" not in st.session_state: st.session_state.form_prop = ""

# --- O TRUQUE DE LIMPEZA SEGURA ---
if "limpar_agora" not in st.session_state: 
    st.session_state.limpar_agora = False

# Se o botão lá embaixo levantou a bandeira, ele limpa a memória ANTES de desenhar a tela
if st.session_state.limpar_agora:
    st.session_state.form_leito = ""
    st.session_state.form_idade = ""
    st.session_state.form_vent = ""
    st.session_state.form_dados = ""
    st.session_state.form_prop = ""
    st.session_state.limpar_agora = False # Abaixa a bandeira

# --- CONEXÃO COM O GOOGLE SHEETS ---
@st.cache_resource
def conectar_google_sheets():
    try:
        # Lê a chave secreta que você salvou na nuvem
        cred_dict = json.loads(st.secrets["google_secret"])
        credentials = Credentials.from_service_account_info(
            cred_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(credentials)
        # Abre a planilha exata do seu Drive
        planilha = client.open("Base_Passometro").sheet1
        return planilha
    except Exception as e:
        st.error(f"⚠️ Erro detalhado: {e}")
        return None

planilha_google = conectar_google_sheets()

# --- FUNÇÃO: COPIAR ÚLTIMO REGISTRO ---
def copiar_ultimo_registro(leito_busca, planilha):
    try:
        dados = planilha.get_all_records()
        
        if not dados:
            return # Se a planilha estiver vazia, não faz nada e segue a vida

        df = pd.DataFrame(dados)

        if 'Leito' not in df.columns:
            st.error("Atenção: A coluna 'Leito' sumiu ou está escrita errado lá na primeira linha do Google Sheets.")
            return

        df['Leito'] = df['Leito'].astype(str).str.strip()
        leito_busca = str(leito_busca).strip()

        historico = df[df['Leito'] == leito_busca]

        if historico.empty:
            st.warning(f"Nenhum registro anterior encontrado para o leito {leito_busca}.")
        else:
            ultimo = historico.iloc[-1]
            
            # Preenche a memória com os dados achados
            st.session_state.form_idade = str(ultimo.get('Idade', ''))
            st.session_state.form_vent = str(ultimo.get('Ventilação Mecânica/VNI/Oxigenioterapia', ''))
            st.session_state.form_dados = str(ultimo.get('Dados Clínicos e Intercorrências', ''))
            st.session_state.form_prop = str(ultimo.get('Proposta Terapêutica', ''))
            
            st.success("Dados copiados com sucesso!")

    except Exception as e:
        st.error(f"Erro ao puxar dados: {e}")

# --- NOVA FUNÇÃO GATILHO DE AUTO-PREENCHIMENTO ---
def auto_preencher():
    planilha = conectar_google_sheets()
    leito_digitado = st.session_state.form_leito
    
    # Só vai na planilha se o usuário digitou alguma coisa
    if leito_digitado != "" and planilha is not None:
        copiar_ultimo_registro(leito_digitado, planilha)

# ==========================================
# INÍCIO DA INTERFACE
# ==========================================
st.title("Passômetro - Fisioterapia UTI Neonatal - HRAD")
st.divider()

st.subheader("Informações do Plantão")
col_data, col_turno = st.columns(2)

with col_data:
    data_plantao = st.date_input("Data do Plantão", format="DD/MM/YYYY")
with col_turno:
    turno = st.radio("Turno", ["Diurno (7h - 19h)", "Noturno (19h - 7h)"], horizontal=True)

st.divider()
st.subheader("Dados do Paciente")

# 1º Lemos o Leito e ligamos o gatilho automático (on_change)
leito = st.text_input("Leito", key="form_leito", on_change=auto_preencher)

# 2º As caixas abaixo vão se preencher sozinhas como mágica!
idade = st.text_input("Idade", key="form_idade")
ventilacao = st.text_input("Ventilação Mecânica/VNI/Oxigenioterapia", key="form_vent")
dados = st.text_area("Dados Clínicos e Intercorrências", key="form_dados")
proposta = st.text_area("Proposta Terapêutica", key="form_prop")

st.divider()

# --- BOTÃO DE AÇÃO PRINCIPAL ---
if st.button("💾 Salvar Plantão e Limpar", type="primary", use_container_width=True):
    if leito == "":
        st.error("O campo 'Leito' é obrigatório!")
    elif planilha_google is None:
        st.error("A conexão com a nuvem falhou.")
    else:
        nova_linha = [
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            data_plantao.strftime("%d/%m/%Y"),
            turno,
            leito,
            idade,
            ventilacao,
            dados,
            proposta
        ]
        
        # Salva no Google Drive
        planilha_google.append_row(nova_linha)
        st.success("Salvo no Google Drive com sucesso!")
        
        # Levanta a bandeira para limpar a tela e reinicia
        st.session_state.limpar_agora = True
        st.rerun()