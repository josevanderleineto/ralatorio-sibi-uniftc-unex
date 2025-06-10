import streamlit as st
import psycopg2
import sqlite3
import pandas as pd
from datetime import datetime
import bcrypt
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente
load_dotenv()
POSTGRES_URI = os.getenv("POSTGRES_URI")

# Conexão com PostgreSQL
conn_pg = psycopg2.connect(POSTGRES_URI)
cursor_pg = conn_pg.cursor()

# Conexão com SQLite
conn_sqlite = sqlite3.connect("relatorios.db", check_same_thread=False)
cursor_sqlite = conn_sqlite.cursor()

# Criar tabela de relatórios se não existir
def criar_tabela_sqlite():
    cursor_sqlite.execute("""
        CREATE TABLE IF NOT EXISTS relatorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            matricula TEXT,
            email TEXT,
            acao TEXT,
            hora TEXT,
            obs TEXT
        )
    """)
    conn_sqlite.commit()

# Valida login
def validar_login(email, senha):
    cursor_pg.execute("SELECT nome, matricula, senha FROM usuarios WHERE email = %s", (email,))
    resultado = cursor_pg.fetchone()
    if resultado:
        nome, matricula, senha_hash = resultado
        if bcrypt.checkpw(senha.encode(), senha_hash.encode()):
            st.session_state.nome = nome
            st.session_state.matricula = matricula
            return True
    return False

# Tela de login
def login():
    st.title("Login - Sistema de Relatórios da Biblioteca")
    email = st.text_input("E-mail")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if validar_login(email, senha):
            st.session_state.logado = True
            st.session_state.email = email
            st.success("Login realizado com sucesso!")
        else:
            st.error("E-mail ou senha inválidos.")

# Tela de cadastro (somente se logado)
def tela_cadastro_usuario():
    st.subheader("Cadastrar novo usuário")
    nome = st.text_input("Nome completo")
    matricula = st.text_input("Matrícula")
    email = st.text_input("E-mail institucional")
    senha = st.text_input("Senha", type="password")

    if st.button("Cadastrar"):
        senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
        try:
            cursor_pg.execute("""
                INSERT INTO usuarios (nome, matricula, email, senha)
                VALUES (%s, %s, %s, %s)
            """, (nome, matricula, email, senha_hash))
            conn_pg.commit()
            st.success("Usuário cadastrado com sucesso!")
        except psycopg2.errors.UniqueViolation:
            conn_pg.rollback()
            st.error("E-mail já cadastrado.")

# Tela de relatórios
def tela_relatorios():
    st.title("Relatórios da Biblioteca")
    st.markdown(f"Usuário: **{st.session_state.nome}** ({st.session_state.email})")

    acao = st.selectbox("Tipo de ação:", ["Abertura da Biblioteca", "Fechamento da Biblioteca", "Atendimento", "Orientação", "Suporte", "Outro"])
    obs = st.text_area("Observações:")

    if st.button("Salvar relatório"):
        hora_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor_sqlite.execute("""
            INSERT INTO relatorios (nome, matricula, email, acao, hora, obs)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            st.session_state.nome,
            st.session_state.matricula,
            st.session_state.email,
            acao,
            hora_atual,
            obs
        ))
        conn_sqlite.commit()
        st.success("Relatório salvo com sucesso!")

    st.subheader("Todos os relatórios cadastrados")
    cursor_sqlite.execute("""
        SELECT nome, matricula, email, acao, hora, obs
        FROM relatorios
        ORDER BY hora DESC
    """)
    dados = cursor_sqlite.fetchall()
    if dados:
        df = pd.DataFrame(dados, columns=["Nome", "Matrícula", "E-mail", "Ação", "Data/Hora", "Observações"])
        st.dataframe(df)
    else:
        st.info("Nenhum relatório encontrado.")

# App principal
def main():
    st.set_page_config(page_title="Relatórios - Biblioteca SIBI", layout="centered")
    criar_tabela_sqlite()

    if "logado" not in st.session_state:
        st.session_state.logado = False

    if st.session_state.logado:
        menu = st.sidebar.selectbox("Menu", ["Relatórios", "Cadastrar Usuário", "Sair"])
        if menu == "Relatórios":
            tela_relatorios()
        elif menu == "Cadastrar Usuário":
            tela_cadastro_usuario()
        elif menu == "Sair":
            st.session_state.logado = False
            st.session_state.clear()
            st.success("Logout realizado.")
    else:
        login()

if __name__ == "__main__":
    main()
