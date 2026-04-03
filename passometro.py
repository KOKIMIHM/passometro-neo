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
# Cria a "bandeira" de aviso se ela não existir
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
        # Puxa os dados da planilha
        dados = planilha.get_all_records()
        
        # 1. Verifica se a planilha está totalmente vazia (só cabeçalho)
        if not dados:
            st.warning("A planilha ainda não possui plantões salvos.")
            return

        # Converte para tabela do Pandas
        df = pd.DataFrame(dados)

        # 2. Verifica se a coluna 'Leito' realmente existe lá no Google Sheets
        if 'Leito' not in df.columns:
            st.error("Atenção: A coluna 'Leito' sumiu ou está escrita errado lá na primeira linha do Google Sheets.")
            return

        # 3. Transforma tudo em texto e limpa espaços invisíveis (evita erro de digitação)
        df['Leito'] = df['Leito'].astype(str).str.strip()
        leito_busca = str(leito_busca).strip()

        # Procura o paciente
        historico = df[df['Leito'] == leito_busca]

        # 4. Se não achar ninguém, avisa. Se achar, copia.
        if historico.empty:
            st.warning(f"Nenhum registro anterior encontrado para o leito {leito_busca}.")
        else:
            ultimo = historico.iloc[-1]
            
            # Joga os dados para a tela
            # Usamos .get() para evitar que o código quebre se alguma outra coluna estiver faltando
            st.session_state.idade = str(ultimo.get('Idade', ''))
            st.session_state.ventilacao = str(ultimo.get('Ventilação', ''))
            st.session_state.dados = str(ultimo.get('Dados/Dieta/Acessos', ''))
            st.session_state.proposta = str(ultimo.get('Proposta', ''))
            
            st.success("Dados copiados com sucesso!")

    except Exception as e:
        st.error(f"Erro ao puxar dados: {e}")

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

# --- FUNÇÃO PARA LIMPAR TUDO ---
def limpar_formulario():
    st.session_state.form_leito = ""
    st.session_state.form_idade = ""
    st.session_state.form_vent = ""
    st.session_state.form_dados = ""
    st.session_state.form_prop = ""

# --- BOTÃO DE AÇÃO PRINCIPAL ---
# Tiramos as colunas para o botão ficar grandão na tela do celular
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
        
        # 1. Salva no Google Drive
        planilha_google.append_row(nova_linha)
        st.success("Salvo no Google Drive com sucesso!")
        
        # 2. Levanta a bandeira para limpar a tela e reinicia
        st.session_state.limpar_agora = True
        st.rerun()