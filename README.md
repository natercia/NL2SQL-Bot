# NL2SQL Bot

This project was originally developed at a previous job for querying the local Data Lakehouse (DLH), and here is a modified version of it, altered to make it generic. The project is currently undocumented because the original documentation was in portuguese.

The NL2SQL bot is a GPT 3.5 powered tool hosted on a Streamlit frontend (its code is contained fully inside one class, in the `st.py` file), where the user can write a query in natural language and obtain a table with data relevant to the answer.
On the front end the user is offered "tips" on how to best write the question, and examples of questions, and after querying is offered the chance to download the data as an `.xlsx` file, or to alter the query produced by GPT in case it is wrong.

The code itself has three phases. First, because it is not possible (due to token constraints) to send the full schema to Open AI, a "mini schema" is sent; in other words, a short description of all tables in the database, and GPT is asked to determine, given the user's question,
which tables it'd need the schema of to formulate an SQL query (that can answer the question).

Then, once the list of tables is obtained, the full schema of these tables (in a NL format) is extracted from the `nltables.txt` file, and sent to GPT, who returns an SQL query that answers the user's original question.

Finally, this quesy is used to obtain relevant data from the local database, and this data is presented to the user on the frontend.

The project can currently not be run as is, because it requires the provision of a valid database into both the `minischema` string and the `nltables.txt` file and of a valid Postgres database connection, but once both have been provided the project can be run after
installing `requirements.txt`and executing:

```streamlit run st.py```

Feel free to use this code for any personal projects. For any questions please open an issue.

That's all:)
