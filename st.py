import streamlit as st
import psycopg2
from sshtunnel import SSHTunnelForwarder
import requests
import json
import pandas as pd
import re
import random
import decimal
from io import BytesIO
from pyxlsb import open_workbook as open_xlsb

#TODO: Add back in documentation that was removed

st.set_page_config(page_title="NL2SQL Bot", page_icon="🤖")
pd.options.display.float_format = '{:,.3f}'.format

def fetch_tables(question):
    miniSchema = f"""Consider the following descriptions of tables in a PostrgeSQL Database:

"
- customer: A table that lists customers, their IDs, their names, addresses and phone numbers.

- order: A table that contains data on all orders placed, their IDs, date they were placed and the ID of the customer that ordered them; REFERENCES TABLE customer. 

- orderitem: A table that contains the IDs of all the products in an order; REFERENCES TABLE order and REFERENCES TABLE product.

- product: A table that contains data on all products sold, their IDs, price and available quantity.
"
Consider the following rules:

"
- **Deliberately go through the question and description word by word** to appropriately answer the question;
"

What tables would be used to answer the following question:  "{question}"
Respond ONLY with a numbered list of the names of the tables, WITHOUT a description.
After identifying the tables, recheck the table descriptions to make sure you are selecting the correct tables.
"""

    
    api_url = "https://api.openai.com/v1/chat/completions"
    proxies = {
        'http': None, 
        'https': None,
    }
    headers = {'Content-Type':'application/json', 'Authorization': 'Bearer [Your API key]'}
    body = {"model":"gpt-3.5-turbo-1106", "messages":[{"role": "user", "content":miniSchema}], "temperature": 0}
    response = requests.post(api_url, headers=headers, json=body, proxies=proxies)
    toReturn = json.loads(response.content.decode(response.encoding)).get("choices")[0].get("message").get("content").split("\n")
    return toReturn

def run_query(query):
    conn = None
    while conn is None:
        try:
            ports = [1543, 2543, 3543, 4543, 6543, 7543, 8543, 9543]
            port = ports[random.randint(0, 7)]
            tunnel = SSHTunnelForwarder(
                ('172.27.26.216', 22),
                ssh_username='ssh_password',
                ssh_password='ssh_username',
                remote_bind_address=('localhost', None),
                local_bind_address=('localhost', port)
            )
            tunnel.start()

            conn = psycopg2.connect(
                database='[Database_Name]',
                user='[User]',
                password='[Password]',
                host=tunnel.local_bind_host,
                port=tunnel.local_bind_port,
            )
            conn.set_session(readonly=True)
            try:
                with conn.cursor() as cur:
                    cur.execute(query)
                    columns = cur.description
                    values = cur.fetchall()
                    conn.close()
                    tunnel.stop()
                    return columns, values
            except psycopg2.InternalError:
                conn.close()
                tunnel.stop()
                return None, None
            except psycopg2.ProgrammingError as err:
                st.write("A query SQL fornecida à base de dados está incorreta, e levantou o seguinte erro:")
                st.write(err)
                st.write("Se a pretender editar, pode fazê-lo dentro da secção \"Como foi obtida esta resposta?\". Senão, pode sempre tentar reformular a sua pergunta.")
                conn.close()
                tunnel.stop()
                return 0, 0 
        except:
            tunnel.stop()
            pass

def click_buttonOne():
    st.session_state.clicked = True

def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    writer.close()
    processed_data = output.getvalue()
    return processed_data

def fetch_sql(tablesList, question):
    file1 = open('nltables.txt', 'r')
    lines = file1.readlines()
    isTable = False
    tablesString = ""
    for l in lines:
        if l.strip() == "--END--":
            isTable = False
        else:
            if (l.replace("TABLE ", "").strip() in tablesList):
                isTable = True
            if isTable:
                tablesString = tablesString + l + "\n"
    
    prompt=f"""
Consider the following descriptions of tables of a POSTRESQL database delimited by ```:
```
{tablesString}
```

Your task is convert a question into a SQL query, given a portion of a postgres database schema.
Adhere to these rules, delimited by ---:
---
- **Deliberately go through the question and database schema word by word** to appropriately answer the question;
- Use Table Aliases to prevent ambiguity. For example, `SELECT table1.col1, table2.col1 FROM table1 JOIN table2 ON table1.id = table2.id`;
- In cases of ambiguity, select *;
- When creating a ratio, always cast the numerator as float;
- Copy the names of the columns correctly;
- Upon recieving a question that requests an Update, reply with "This prompt requires modifying the table, please select another prompt.".
---

Considering all these rules and the provided schema, you must generate a Single SQL query for the question in quotations: "{question}"

Provide a step by step answer, including explanations, and include the SQL between ``` delimitators.

After generating the PostresSQL query, CAREFULLY go over the table descriptions of the tables again to make sure you are copying the names of the columns correctly, answering what the question is asking and adhering to the rules.
"""

    api_url = "https://api.openai.com/v1/chat/completions"
    proxies = {
        'http': None, 
        'https': None,
    }
    headers = {'Content-Type':'application/json', 'Authorization': 'Bearer [Your API Key]'}
    body = {"model":"gpt-3.5-turbo-1106", "messages":[{"role": "user", "content": prompt}], "temperature": 0}
    response = requests.post(api_url, headers=headers, json=body, proxies=proxies)
    response = json.loads(response.content.decode(response.encoding)).get("choices")[0].get("message").get("content").split("\n")
    toReturn = ""
    for r in response:
        toReturn = toReturn + r + "\n"
    return toReturn

def rerun_query(q):
    st.session_state.query = q
    st.session_state.isRerun= True
    st.session_state.button = False

def setQuery(q):
    st.session_state.query = q

def App1page():
    query = st.session_state.query
    if ("INSERT" in query.upper()) or ("UPDATE" in query.upper()) or ("DROP" in query.upper()) or ("CREATE" in query.upper()) or ("DELETE" in query.upper()) or ("ALTER" in query.upper()):
        st.write("Esta query requer a modificação da tabela. Por favor, reformule a sua pergunta, ou faça uma nova questão.")
        
    else:
        columnsPre, valuesPre = run_query(query)
        if columnsPre == None and valuesPre == None:
            st.write("Esta query requer a modificação da tabela. Por favor, reformule a sua pergunta, ou faça uma nova questão.")
        else:
            if columnsPre != 0 and valuesPre != 0:
                columns = []
                i = 0
                for c in columnsPre:
                    i += 1
                    columns.append(c[0])
                values = []
                for vPLine in valuesPre:
                    v = []
                    for vPElement in vPLine:
                        if isinstance(vPElement, decimal.Decimal):
                            v.append(str(vPElement).replace(".",","))
                        else:
                            v.append(vPElement)
                    values.append(v)
                df = pd.DataFrame(values, columns = columns)
                st.dataframe(df)
                df_xlsx = to_excel(df)
                st.download_button(label='📥 Descarregar Tabela',
                                data=df_xlsx ,
                                file_name= 'download.xlsx')
    with st.expander("Como é que foi obtida esta resposta?"): 
        st.write("Tabelas da Base de Dados selecionadas pelo chatGPT para fazer a query:")
        for t in st.session_state.tables:
            if(t in query):
                st.markdown(t)
        st.markdown(" ")
        queryNova = ""
        queryNova = st.text_area(label="Query gerada pelo ChatGPT. Se detetar algum erro, altere a query e re-envie:", value = query, height = 300, on_change = setQuery(queryNova))
        submitted = st.button(label = "Re-enviar", on_click = rerun_query(queryNova))
        if submitted:
            st.session_state.button = False
            st.rerun()
        
            

if "button" not in st.session_state:
    st.session_state.button = False

if "query" not in st.session_state:
    st.session_state.query = None
    st.session_state.tables = None

st.title("🤖 NL2SQL BOT")
st.write(" ")
question = st.text_area(label="Insira a pergunta (em inglês)")
with st.expander("Dicas para escrever a pergunta"):
    st.markdown("""O NL2SQL Bot é uma tool powered by GPT 3.5 que permite fazer querys à Base de Dados usando linguagem natural. 
Para melhorar a qualidade das respostas obtidas, é necessário fazer uma pergunta clara, objetiva e específica, para que a resposta também o seja. Ficam aqui algumas sugestões para otimizar a escrita das perguntas:
- Devemos fazer a pergunta como se estivessemos a falar com alguém que percebe pouco do conteúdo das tabelas; quanto mais detalhe, melhor.
- Se pedirmos os valores referentes a um ano, muitas vezes o NL2SQL bot irá responder com todos os valores correspondentes a esse ano, levando a alguma ambíguidade. Nesse caso, devemos ou especificar a data, ou adicionar “Include the date” ao fim da pergunta para podermos discernir entre os diferentes valores.
- Recomenda-se evitar expressões vagas, por exemplo em vez de dizer "current", pedir antes a data exata, ou dizer “latest”, “most recent”, etc.
- O ChatGPT/GPT 3.5 é conhecido por por vezes "ignorar" algumas partes do que dizemos. Se tal acontecer, podemos capitalizar as partes ignoradas, ou então reformular a pergunta.

O ChatGPT/GPT 3.5, tal como todos os modelos de linguagem, pode sofrer de ["alucinações"](https://pt.wikipedia.org/wiki/Alucina%C3%A7%C3%A3o_(intelig%C3%AAncia_artificial)), e por isso não conseguir gerar uma query certa. Se não obtiver uma resposta certa à primeira, não
hesite em voltar a carregar no botão query (por vezes pensar duas vezes ajuda o ChatGPT a "perceber" melhor), ou em reformular a pergunta para ser mais específico.
""")
    st.write(" ")
with st.expander("Exemplos de perguntas"):
    st.write("Alguns exemplos de perguntas, das quais se pode fazer copy & paste, e modificar à medida do que é pretendido saber.")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""EXAMPLE A
""")
    with col2:
        st.markdown("""EXAMPLE B
""")
        st.markdown("")
    st.write(" ")
btn1 = st.button("Query")
if btn1:
    st.session_state.button = True
if st.session_state.query != None and st.session_state.button == False:
    st.session_state.button = False
    App1page()
elif st.session_state.button:
    tablesPre = fetch_tables(question)

    st.session_state.tables = []
    for t in tablesPre:
        splitted = t.split(".")
        st.session_state.tables.append(splitted[1].strip())
    response = fetch_sql(st.session_state.tables, question)
    if response == "This prompt requires modifying the table, please select another prompt.":
        st.write("Esta query requer a modificação da tabela. Por favor, reformule a sua pergunta, ou faça uma nova questão.")
    else:
        queryGPT = re.findall(r'\`\`\`([^]]*)\`\`\`', response)[0]
        if "sql" in queryGPT:
            queryGPT = queryGPT.replace("sql", "")
        if "like" in queryGPT :
            queryGPT = queryGPT.replace("like", "ILIKE")
        elif "LIKE" in queryGPT :
            queryGPT = queryGPT.replace("LIKE", "ILIKE")

    st.session_state.query = queryGPT
    App1page()