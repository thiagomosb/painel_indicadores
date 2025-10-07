import os
import time
import streamlit as st
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate


def app():
    # 🔹 Chave da OpenAI
    os.environ["OPENAI_API_KEY"] = ''

    # 🔹 Embeddings (mesmo modelo usado no 01_ingest.py)
    embedding = OpenAIEmbeddings(model="text-embedding-3-small")

    # 🔹 Carregar banco vetorial existente
    vector_store = Chroma(
        persist_directory="db",
        collection_name="pops_collection",
        embedding_function=embedding
    )
    retriever = vector_store.as_retriever()

    # 🔹 Modelo de conversa
    model = ChatOpenAI(model="gpt-4o-mini")

    # 🔹 Prompt do agente
    system_prompt = """
    Você é um agente especialista em elaborar DDSs (Diálogos Diários de Segurança) e materiais de Treinamento com base nos Processos Operacionais Padrão (POPs).
    Seu conhecimento vem exclusivamente do banco vetorial criado a partir dos arquivos PDF armazenados na pasta "POPs".

    📌 Regras de atuação:
    - Crie DDSs e treinamentos somente com base nos POPs disponíveis.
    - Caso a informação não esteja registrada, responda claramente: 
    👉 "Não encontrei essa informação nos POPs disponíveis."
    - DDS deve ser curto, objetivo e prático.
    - Treinamento pode ser mais detalhado e estruturado.
    - Sempre finalize com as referências dos POPs utilizados.

    📖 Exemplo DDS:
    "Tema: Uso correto de EPI’s
    Antes de iniciar a atividade, verifique se todos os EPIs obrigatórios estão em boas condições e devidamente ajustados.
    📖 Referência: POP_03_Segurança.pdf"
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Contexto do documento:\n{context}\n\nPergunta:\n{input}"),
    ])

    # 🔹 Cadeia de QA
    question_answer_chain = create_stuff_documents_chain(
        llm=model,
        prompt=prompt,
        document_variable_name="context"
    )
    chain = create_retrieval_chain(
        retriever=retriever,
        combine_docs_chain=question_answer_chain,
    )

    # ----------------- STREAMLIT APP -----------------
    st.set_page_config(page_title="Chat DDS - POPs", page_icon="📚", layout="centered")

    st.title("💬 Chat DDS & Treinamentos (POPs)")

    # Inicializa histórico
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Mostrar histórico de mensagens
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input do usuário
    if prompt_user := st.chat_input("Digite sua pergunta sobre os POPs..."):
        # Mostrar pergunta do usuário
        st.chat_message("user").markdown(prompt_user)
        st.session_state["messages"].append({"role": "user", "content": prompt_user})

        # Gerar resposta
        try:
            response = chain.invoke({"input": prompt_user})
            answer = response["answer"]

        except Exception as e:
            if "Rate limit" in str(e):
                answer = "⚠️ Limite de taxa atingido, tente novamente em alguns segundos."
                time.sleep(10)
            else:
                answer = f"❌ Ocorreu um erro: {e}"

        # Mostrar resposta do assistente
        with st.chat_message("assistant"):
            st.markdown(answer)
        st.session_state["messages"].append({"role": "assistant", "content": answer})



