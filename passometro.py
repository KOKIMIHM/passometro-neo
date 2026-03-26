import streamlit as st
import pandas as pd
from datetime import datetime
import json
import gspread
from google.oauth2.service_account import Credentials

# Configuração da página
st.set_page_config(page_title="Passômetro UTI Neo", layout="wide")

# --- INICIALIZANDO A MEMÓRIA DO APLICATIVO ---
if "form_leito" not in st.session_state: st.session_state.form_leito = ""
if "form_idade" not in st.session_state: st.session_state.form_idade = ""
if "form_vent" not in st.session_state: st.session_state.form_vent = ""
if "form_dados" not in st.session_state: st.session_state.form_dados = ""
if "form_prop" not in st.session_state: st.session_state.form_prop = ""

# --- CONEXÃO COM O GOOGLE SHEETS ---
@st.cache_resource
def conectar_google_sheets():
    try:
        # Lê a chave secreta que você salvou na nuvem
        cred_dict = json.loads(st.secrets["google_secret"])
        credentials = Credentials.from_service_account_info(
            cred_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(credentials)
        # Abre a planilha exata do seu Drive
        planilha = client.open("Base_Passometro").sheet1
        return planilha
    except Exception as e:
        st.error("⚠️ Não foi possível conectar ao Google Sheets. Verifique os Secrets.")
        return None

planilha_google = conectar_google_sheets()

# --- FUNÇÃO: COPIAR ÚLTIMO REGISTRO ---
def copiar_ultimo_registro():
    if planilha_google is not None:
        dados = planilha_google.get_all_records()
        if len(dados) > 0:
            df = pd.DataFrame(dados)
            leito_atual = str(st.session_state.form_leito).strip()
            
            if leito_atual != "":
                df['Leito'] = df['Leito'].astype(str)
                df_filtrado = df[df['Leito'] == leito_atual]
                
                if not df_filtrado.empty:
                    ultima_linha = df_filtrado.iloc[-1]
                    st.session_state.form_idade = str(ultima_linha.get("Idade/Dias", ""))
                    st.session_state.form_vent = str(ultima_linha.get("Ventilação", ""))
                    st.session_state.form_dados = str(ultima_linha.get("Dados Clínicos", ""))
                    st.session_state.form_prop = str(ultima_linha.get("Proposta Terapêutica", ""))
                else:
                    st.warning(f"Nenhum registro anterior encontrado para o leito {leito_atual}.")
            else:
                st.warning("Por favor, digite o número do Leito antes de clicar em Copiar.")

# ==========================================
# INÍCIO DA INTERFACE
# ==========================================
st.title("Passômetro - Fisioterapia UTI Neonatal")
st.divider()

st.subheader("Informações do Plantão")
col_data, col_turno = st.columns(2)

with col_data:
    data_plantao = st.date_input("Data do Plantão", format="DD/MM/YYYY")
with col_turno:
    turno = st.radio("Turno", ["Diurno (7h - 19h)", "Noturno (19h - 7h)"], horizontal=True)

st.divider()

# --- SESSÃO: DADOS DO PACIENTE ---
st.subheader("Paciente e Parâmetros")

st.button("🔄 Copiar último registro deste Leito", on_click=copiar_ultimo_registro, type="secondary")

col1, col2 = st.columns(2)

with col1:
    leito = st.text_input("Leito e Nome do Paciente", key="form_leito")
with col2:
    idade = st.text_input("Idade Gestacional / Dias de Vida", key="form_idade")

ventilacao = st.text_area("Parâmetros Ventilatórios Atuais (VM/VNI/Cateter)", height=100, key="form_vent")
dados = st.text_area("Dados Clínicos e Intercorrências", height=100, key="form_dados")

st.subheader("Proposta Terapêutica")
proposta = st.text_area("Condutas", height=100, key="form_prop")

# --- BOTÃO DE SALVAR NO GOOGLE ---
if st.button("Salvar Plantão", type="primary"):
    if leito == "":
        st.error("O campo 'Leito' é obrigatório!")
    elif planilha_google is None:
        st.error("A conexão com a nuvem falhou.")
    else:
        # Prepara a linha exata com as colunas da sua planilha
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
        
        # Envia direto para o Google Drive
        planilha_google.append_row(nova_linha)
        st.success(f"Passômetro do leito {leito} salvo no Google Drive com sucesso!")

# --- SESSÃO: LENDO O HISTÓRICO DA NUVEM ---
st.divider()
st.subheader("📚 Histórico de Plantões (Google Sheets)")

if planilha_google is not None:
    dados_planilha = planilha_google.get_all_records()
    if len(dados_planilha) > 0:
        tabela_historico = pd.DataFrame(dados_planilha)
        st.dataframe(tabela_historico, use_container_width=True)
    else:
        st.info("A planilha está vazia. Salve o primeiro paciente para testar!")