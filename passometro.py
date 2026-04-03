import streamlit as st
import pandas as pd
from datetime import datetime
import json
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF

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

if st.session_state.limpar_agora:
    st.session_state.form_leito = ""
    st.session_state.form_idade = ""
    st.session_state.form_vent = ""
    st.session_state.form_dados = ""
    st.session_state.form_prop = ""
    st.session_state.limpar_agora = False

# --- CONEXÃO COM O GOOGLE SHEETS ---
@st.cache_resource
def conectar_google_sheets():
    try:
        cred_dict = json.loads(st.secrets["google_secret"])
        credentials = Credentials.from_service_account_info(
            cred_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(credentials)
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
        if not dados: return 

        df = pd.DataFrame(dados)
        if 'Leito' not in df.columns: return

        df['Leito'] = df['Leito'].astype(str).str.strip()
        leito_busca = str(leito_busca).strip()

        historico = df[df['Leito'] == leito_busca]

        if not historico.empty:
            ultimo = historico.iloc[-1]
            st.session_state.form_idade = str(ultimo.get('Idade', ''))
            st.session_state.form_vent = str(ultimo.get('Ventilação Mecânica', ''))
            st.session_state.form_dados = str(ultimo.get('Dados Clínicos e Intercorrências', ''))
            st.session_state.form_prop = str(ultimo.get('Proposta Terapêutica', ''))
            st.success("Histórico puxado com sucesso!")

    except Exception as e:
        st.error(f"Erro ao puxar dados: {e}")

# --- NOVA FUNÇÃO: GERADOR DE PDF ---
def gerar_pdf(data_plantao, turno, leito, idade, vent, dados, prop):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho
    pdf.set_font("helvetica", style="B", size=16)
    pdf.cell(0, 10, "Passômetro Diário - UTI Neonatal HRAD", new_x="LMARGIN", new_y="NEXT", align="C")
    
    pdf.set_font("helvetica", size=12)
    pdf.cell(0, 10, f"Data: {data_plantao}   |   Turno: {turno}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.line(10, 30, 200, 30)
    pdf.ln(10)
    
    # Corpo do Documento
    pdf.set_font("helvetica", style="B", size=12)
    pdf.cell(0, 8, f"Leito e Nome do Paciente: {leito}      Idade: {idade}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    pdf.set_font("helvetica", style="B", size=12)
    pdf.cell(0, 8, "Ventilação Mecânica:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", size=12)
    pdf.multi_cell(0, 8, vent if vent else "N/A")
    pdf.ln(5)
    
    pdf.set_font("helvetica", style="B", size=12)
    pdf.cell(0, 8, "Dados Clínicos e Intercorrências:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", size=12)
    pdf.multi_cell(0, 8, dados if dados else "N/A")
    pdf.ln(5)
    
    pdf.set_font("helvetica", style="B", size=12)
    pdf.cell(0, 8, "Proposta Terapêutica:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", size=12)
    pdf.multi_cell(0, 8, prop if prop else "N/A")
    
    # Retorna o arquivo pronto em formato de bytes
    return bytes(pdf.output())

# --- GATILHO DE AUTO-PREENCHIMENTO ---
def auto_preencher():
    planilha = conectar_google_sheets()
    leito_digitado = st.session_state.form_leito
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

leito = st.text_input("Leito e Nome do Paciente", key="form_leito", on_change=auto_preencher)
idade = st.text_input("Idade", key="form_idade")
ventilacao = st.text_input("Ventilação Mecânica", key="form_vent")
dados = st.text_area("Dados Clínicos e Intercorrências", key="form_dados", height=150)
proposta = st.text_area("Proposta Terapêutica", key="form_prop", height=100)

st.divider()

# --- ÁREA DE SALVAMENTO E PDF ---
if st.button("💾 Salvar Plantão", type="primary", use_container_width=True):
    if leito == "":
        st.error("O campo 'Leito' é obrigatório!")
    elif planilha_google is None:
        st.error("A conexão com a nuvem falhou.")
    else:
        # Prepara a linha
        data_formatada = data_plantao.strftime("%d/%m/%Y")
        nova_linha = [
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            data_formatada, turno, leito, idade, ventilacao, dados, proposta
        ]
        
        # 1. Salva no Google
        planilha_google.append_row(nova_linha)
        
        # 2. Gera o PDF e guarda na memória
        pdf_bytes = gerar_pdf(data_formatada, turno, leito, idade, ventilacao, dados, proposta)
        st.session_state.pdf_pronto = pdf_bytes
        st.session_state.nome_arquivo = f"Evolucao_Leito_{leito}.pdf"
        
        st.success("✅ Salvo no Google Drive com sucesso!")

# --- SE O PDF ESTIVER PRONTO, MOSTRA OS BOTÕES ESCONDIDOS ---
if "pdf_pronto" in st.session_state:
    col_pdf, col_limpar = st.columns(2)
    
    with col_pdf:
        # Botão mágico do Streamlit que faz o download do arquivo
        st.download_button(
            label="📄 Baixar em PDF",
            data=st.session_state.pdf_pronto,
            file_name=st.session_state.nome_arquivo,
            mime="application/pdf",
            use_container_width=True
        )
        
    with col_limpar:
        # Botão para limpar a tela para o próximo paciente
        if st.button("🧹 Limpar Campos", use_container_width=True):
            del st.session_state.pdf_pronto
            st.session_state.limpar_agora = True
            st.rerun()