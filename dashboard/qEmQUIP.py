import streamlit as st
import pandas as pd
import plost
import mysql.connector
import numpy as np
import altair as alt
from htbuilder import HtmlElement, div, ul, li, br, hr, a, p, img, styles, classes, fonts
from htbuilder.units import percent, px
from htbuilder.funcs import rgba, rgb

# MySQL connection parameters
mysql_config = {
    'user': 'handy',
    'password': 'handy',
    'host': 'ec2-3-80-240-233.compute-1.amazonaws.com',
    'database': 'calibration_data'
}

# Connect to the MySQL database
conn = mysql.connector.connect(**mysql_config)
cursor = conn.cursor()

st.set_page_config(layout='wide', initial_sidebar_state='expanded')

with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

#region Sidebar

st.sidebar.header('qEmQUIP')

cursor.execute('''SELECT user_id, name FROM user WHERE inactive IS NULL  ''')
results = cursor.fetchall()

user_id_options = {}

for i in results:
    user_id_options[i[0]] = "{} - {}".format(i[0], i[1])

user_id = st.sidebar.selectbox("User ID", options=list(user_id_options.keys()), format_func=lambda x: user_id_options[x])


cursor.execute('''SELECT DISTINCT name FROM circuit c INNER JOIN result_header h ON c.circuit_ID = h.circuit_ID
               WHERE h.user_id = %s
               ''', (user_id, ))
results = cursor.fetchall()

par_circuits = []

for i in results:
    par_circuits.append(i[0])

st.sidebar.subheader('Circuit parameter')
circuit = st.sidebar.selectbox('Circuit name', par_circuits) 


cursor.execute('''SELECT id, created_datetime  FROM result_header h INNER JOIN circuit c ON h.circuit_id = c.circuit_id 
               WHERE c.name = %s AND h.user_id = %s ''', (circuit, user_id, ))
results = cursor.fetchall()

par_headers_options = {}

for i in results:
    par_headers_options[i[0]] = "{} - {}".format(str(i[0]), i[1].strftime('%Y-%m-%d %H:%M'))

header = st.sidebar.selectbox("Batch ID", options=list(par_headers_options.keys()), format_func=lambda x: par_headers_options[x])

st.sidebar.subheader('Optimization parameters')

#region Sidebar Qiskit
st.sidebar.write("#### Qiskit Optimization")
st.sidebar.write("##### (L: layout, R: routing)")

qiskit = st.sidebar.checkbox('Select All', key="q-all")

qiskit_optimization = {
    'Level 0 - No optimization (L: trivial, R: stochastic)': False,
    'Level 1 - Adjacent gate collapsing (L: error-aware and dense, R: Sabre)': False,
    'Level 2 - Gate cancellation (L: Sabre, R: Sabre)': False,
    'Level 3 - Gate cancellation and unitary synthesis (L: Sabre, R: Sabre)': False,
}

qiskit_sabre_default_value = False
qiskit_mirage_default_value = False

if qiskit:
    for key in qiskit_optimization:
        qiskit_optimization[key] = True

    qiskit_sabre_default_value = True
    qiskit_mirage_default_value = True

for key, value in qiskit_optimization.items():
    qiskit_optimization[key] = st.sidebar.checkbox(key, value, key="q-q-" + key)

st.sidebar.write("##### Routing method")

# qiskit_sabre = st.sidebar.checkbox("Sabre", qiskit_sabre_default_value, key="q-sabre")
qiskit_mirage = st.sidebar.checkbox("Mirage - Mirror gate insertion (Sabre layout and routing)", qiskit_mirage_default_value, key="q-mirage")

#endregion

st.sidebar.markdown('---')

#region Sidebar TriQ

st.sidebar.write("#### TriQ Optimization")

triq = st.sidebar.checkbox('Select All', key="t-all")

triq_optimization = {
    'Level 0 - Default qubit mapping': False,
    'Level 1 - Communication-optimized mapping': False,
    'Level 2 - Comm-and Noise-optimized mapping': False
}

triq_qiskit_optimization = {
    'Level 0 - No optimization (trivial layout, stochastic routing)': False,
    'Level 1 - Adjacent gate collapsing (error-aware and dense layout, Sabre routing)': False,
    'Level 2 - Gate cancellation (Sabre layout and routing)': False,
    'Level 3 - Gate cancellation and unitary synthesis (Sabre layout and routing)': False,
}


triq_sabre_default_value = False
triq_qiskit_before_default_value = False
triq_qiskit_after_default_value = False
if triq:
    for key in triq_optimization:
        triq_optimization[key] = True

    for key in triq_qiskit_optimization:
        triq_qiskit_optimization[key] = True

    triq_sabre_default_value = True
    triq_qiskit_before_default_value = True
    triq_qiskit_after_default_value = True

for key, value in triq_optimization.items():
    triq_optimization[key] = st.sidebar.checkbox(key, value, key="t-t-" + key)

st.sidebar.write("##### Qiskit optimization to TriQ :")

for key, value in triq_qiskit_optimization.items():
    triq_qiskit_optimization[key] = st.sidebar.checkbox(key, value, key="t-q-" + key)

#endregion

st.sidebar.markdown('---')

#region Sidebar SCR

st.sidebar.write("#### SCR Optimization")

laura = st.sidebar.checkbox('Select All', key="l-all")

laura_optimization = {
    'Level 2 - Comm-and Noise-optimized mapping': False
}

laura_qiskit_optimization = {
    'Level 3 - Gate cancellation and unitary synthesis (Sabre layout and routing)': False,
}

laura_sabre_default_value = False
if laura:
    for key in laura_optimization:
        laura_optimization[key] = True

    for key in laura_qiskit_optimization:
        laura_qiskit_optimization[key] = True

for key, value in laura_optimization.items():
    laura_optimization[key] = st.sidebar.checkbox(key, value, key="l-l-" + key)


st.sidebar.write("##### Qiskit optimization to SCR :")

for key, value in laura_qiskit_optimization.items():
    laura_qiskit_optimization[key] = st.sidebar.checkbox(key, value, key="l-q-" + key)

#endregion

#region Mirage
# st.sidebar.markdown('---')

# mirage = st.sidebar.checkbox('Select All - Mirage')

# mirage_qiskit_optimization = {
#     'Level 0': False,
#     'Level 1': False,
#     'Level 2': False,
#     'Level 3': False
# }

# if mirage:
#     for key in mirage_qiskit_optimization:
#         mirage_qiskit_optimization[key] = True

# for key, value in mirage_qiskit_optimization.items():
#     mirage_qiskit_optimization[key] = st.sidebar.checkbox(key, value, key="m-q-" + key)
#endregion

#endregion

#region Getting the SQL

base_sql = '''SELECT job_id, detail_id, qiskit_optimization, apply_qiskit, triq_optimization, sabre, mirage, laura_optimization,
        success_nassc, success_tvd, success_hellinger, total_gate, total_gate_cx, qubit_gate_count_1q, qubit_gate_count_2q,
        circuit_depth, circuit_cost, execution_time
        FROM calibration_data.result WHERE header_id = {} AND status = "done" '''.format(header)

#region qiskit sql

qiskit_sql = ""
qiskit_sabre_sql = ""
qiskit_mirage_sql = ""

if any(qiskit_optimization.values()):
    qiskit_sql = base_sql + " AND triq_optimization IS NULL AND laura_optimization IS NULL "

    opt_tmp = ""
    for key, value in qiskit_optimization.items():
        if key == "Select All":
            continue
        tmp_key = key.split("-")[0].split(" ") 
        if qiskit_optimization[key] and tmp_key[0] == "Level":
            opt_tmp += "{},".format(tmp_key[1])
        
    if opt_tmp != "":
        qiskit_sql += " AND qiskit_optimization IN ({})".format(opt_tmp [:-1])

    # if (qiskit_sabre):
    #     qiskit_sabre_sql += qiskit_sql + " AND sabre = 1 "
        
    if (qiskit_mirage):
        qiskit_mirage_sql += qiskit_sql + " AND mirage = 1 "

    qiskit_sql += " AND sabre = 0 AND mirage = 0"
    
else:
    qiskit_sql = ""

sql = qiskit_sql

# if (qiskit_sabre_sql != ""):
#     sql += " UNION " + qiskit_sabre_sql

if (qiskit_mirage_sql != ""):
    sql += " UNION " + qiskit_mirage_sql

#endregion

#region triq sql
triq_sql = ""
triq_qiskit_sql = ""
triq_sabre_sql = ""

if any(triq_optimization.values()):
    opt_tmp = ""
    triq_sql = base_sql + " AND triq_optimization is not NULL AND laura_optimization IS NULL "
    for key, value in triq_optimization.items():
        if key == "Select All":
            continue
        tmp_key = key.split(" - ")[0].split(" ") 
        if triq_optimization[key] and [0] == "Level":
            opt_tmp += "{},".format(tmp_key[1])
        
    if opt_tmp != "":
        triq_sql += " AND triq_optimization IN ({})".format(opt_tmp [:-1])


    if any(triq_qiskit_optimization.values()):
        opt_tmp = ""
        for key, value in triq_qiskit_optimization.items():
            tmp_key = key.split(" - ")[0].split(" ")
            if triq_qiskit_optimization[key] and tmp_key[0] == "Level":
                opt_tmp += "{},".format(tmp_key[1])
            
        if opt_tmp != "":
            triq_qiskit_sql += triq_sql + " AND (qiskit_optimization IN ({}) or qiskit_optimization IS NULL )".format(opt_tmp [:-1])

        triq_qiskit_sql += " AND sabre = 0  AND apply_qiskit = 'after' "

    else:
        triq_sql += " AND qiskit_optimization IS NULL "


    triq_sql += " AND apply_qiskit IS NULL "

    if sql != "":
        sql += " UNION " + triq_sql
    else:
        sql = triq_sql

else:
    triq_sql = ""

if (triq_qiskit_sql != ""):
    sql += " UNION " + triq_qiskit_sql

if (triq_sabre_sql != ""):
    sql += " UNION " + triq_sabre_sql

#endregion 

#region SCR sql
laura_sql = ""
laura_qiskit_sql = ""
laura_sabre_sql = ""

if any(laura_optimization.values()):
    opt_tmp = ""
    laura_sql = base_sql + " AND laura_optimization is not NULL AND triq_optimization IS NULL "
    for key, value in laura_optimization.items():
        if key == "Select All":
            continue
        tmp_key = key.split(" - ")[0].split(" ") 
        if laura_optimization[key] and tmp_key[0] == "Level":
            opt_tmp += "{},".format(tmp_key[1])
        
    if opt_tmp != "":
        laura_sql += " AND laura_optimization IN ({})".format(opt_tmp [:-1])

    opt_tmp = ""
    for key, value in laura_qiskit_optimization.items():
        tmp_key = key.split(" - ")[0].split(" ")
        if laura_qiskit_optimization[key] and tmp_key[0] == "Level":
            opt_tmp += "{},".format(tmp_key[1])
        
    if opt_tmp != "":
        laura_qiskit_sql += laura_sql + " AND (qiskit_optimization IN ({}) or qiskit_optimization IS NULL )".format(opt_tmp [:-1])


    laura_sql += " AND apply_qiskit IS NULL AND qiskit_optimization IS NULL "

    if sql != "":
        sql += " UNION " + laura_sql
    else:
        sql = laura_sql

else:
    laura_sql = ""

if (laura_qiskit_sql != ""):
    sql += " UNION " + laura_qiskit_sql


#endregion 

#region Mirage
# mirage_sql = base_sql + " AND mirage is NULL AND sabre IS NULL " ### NEED TO FIX THIS LATER

# if any(mirage_qiskit_optimization.values()):
#     opt_tmp = ""
#     for key, value in mirage_qiskit_optimization.items():
#         if mirage_qiskit_optimization[key] and key.split(" ")[0] == "Level":
#             opt_tmp += "{},".format(key.split(" ")[1])
        
#     if opt_tmp != "":
#         mirage_sql += " AND qiskit_optimization IN ({})".format(opt_tmp [:-1])
# else:
#     mirage_sql += " AND qiskit_optimization IS NULL "

# sql += " UNION " + mirage_sql
#endregion

if (sql == ""):
    cursor.close()
    conn.close()
else:

    cursor.execute(sql)
    results = cursor.fetchall()

    #endregion

    #region Data Processing
    opt = []
    nassc = []
    tvd = []
    job_id = []
    hellinger = []
    total_gate = []
    total_gate_cx = []
    qubit_gate_count_1q = []
    qubit_gate_count_2q = []
    circuit_depth = []
    circuit_cost = []
    execution_time = []

    for res in results:
        _job_id, _detail_id, _qiskit_optimization, _apply_qiskit, _triq_optimization, _sabre,\
            _mirage, _laura_optimization, _success_nassc, _success_tvd, _success_hellinger,\
                _total_gate, _total_gate_cx, _qubit_gate_count_1q, _qubit_gate_count_2q, _circuit_depth, _circuit_cost, _execution_time = res
        opt_name = ""

        if _triq_optimization != None:
            opt_name += "T_{}_".format(_triq_optimization)

        if _laura_optimization != None:
            opt_name += "SCR_" 

        if _apply_qiskit != None:
            # # apply = "b" if _apply_qiskit == "before" else "a" 
            # opt_name += "Q_{}_{}_".format(apply, _qiskit_optimization)

            opt_name += "Q_{}_".format(_qiskit_optimization)

        elif _sabre == None and _mirage == None: ## still need to fix this related to mirage
            opt_name += "M_{}_".format(_qiskit_optimization)
        elif _triq_optimization == None and _laura_optimization == None:
            opt_name += "Q_{}_".format(_qiskit_optimization)

        # if _sabre:
        #     opt_name += "sabre_" 

        if _mirage:
            opt_name += "mirage_"

        opt_name = "({}) {}".format(_detail_id, opt_name[:-1] )

        job_id.append(_job_id)
        opt.append(opt_name)
        nassc.append(float(_success_nassc))
        tvd.append(float(_success_tvd))
        hellinger.append(1 - float(_success_hellinger))
        total_gate.append(float(_total_gate))
        qubit_gate_count_1q.append(float(_qubit_gate_count_1q))
        qubit_gate_count_2q.append(float(_qubit_gate_count_2q))
        circuit_depth.append(float(_circuit_depth))
        circuit_cost.append(float(_circuit_cost))
        execution_time.append(float(_execution_time))

    #endregion

    data = pd.DataFrame({
        'opt': opt,
        'NASSC': nassc,
        'TVD': tvd,
        'Hellinger': hellinger,
        'job_id': job_id,
        'total_gate': total_gate,
        'qubit_gate_count_1q': qubit_gate_count_1q,
        'qubit_gate_count_2q': qubit_gate_count_2q,
        'circuit_depth': circuit_depth,
        'circuit_cost': circuit_cost,
        'execution_time': execution_time,
    })

    # plot_opt = st.sidebar.multiselect('Select data', opt, [])

    cursor.execute('''SELECT c.name, c.depth, c.total_gates, JSON_EXTRACT(`c`.`correct_output`, '$') AS `correct_output`, 
                h.created_datetime FROM calibration_data.circuit c
                    INNER JOIN calibration_data.result_header h ON c.circuit_id = h.circuit_id 
                    WHERE h.id = %s AND h.user_id = %s  
                                ''', (header, user_id, ))
    results = cursor.fetchall()

    circuit_name, depth, total_gates, correct_output, created_datetime = results[0]

    # Row 1
    st.markdown('# Metrics')
    row_1_col1, row_1_col2, row_1_col3 = st.columns(3)
    row_1_col1.metric("Circuit Name", circuit_name)
    row_1_col2.metric("Total gates", total_gates)
    row_1_col3.metric("Depth", depth)
    

    # Row 2
    row_2_col1, = st.columns(1)
    row_2_col1.metric("Correct output", correct_output)
    

    # success_rate_data = ['TVD', 'NASSC', 'Hellinger']

    # # , 'total_gate', 'qubit_gate_count_1q', 'qubit_gate_count_2q', 'circuit_depth', 'circuit_cost', 'execution_time'

    # st.sidebar.subheader('Group chart')
    # success_rate = st.sidebar.multiselect('Select data', success_rate_data, success_rate_data)

    if opt:

        st.markdown('## ' + circuit + " - Metric: 1 - TVD (Success rate)")
        new_data = pd.DataFrame({
                    'Optimization': data["opt"],
                    'Success rate': data["TVD"],
                })
        st.bar_chart(new_data, x="Optimization", y="Success rate")

        st.markdown('## ' + circuit + " - Metric: NASSC (Success rate)")
        new_data = pd.DataFrame({
                    'Optimization': data["opt"],
                    'Success rate': data["NASSC"],
                })
        st.bar_chart(new_data, x="Optimization", y="Success rate")

        st.markdown('## ' + circuit + " - Metric: 1 - Hellinger (Correlation)")
        new_data = pd.DataFrame({
                    'Optimization': data["opt"],
                    'Correlation': data["Hellinger"],
                })
        st.bar_chart(new_data, x="Optimization", y="Correlation")
    
        st.markdown('## ' + circuit + " - Metric: Total gate")
        new_data = pd.DataFrame({
                    'Optimization': data["opt"],
                    'Total gate': data["total_gate"],
                })
        st.bar_chart(new_data, x="Optimization", y="Total gate")

        st.markdown('## ' + circuit + " - Metric: Total 1 qubit gate")
        new_data = pd.DataFrame({
                    'Optimization': data["opt"],
                    'Total 1 qubit gate': data["qubit_gate_count_1q"],
                })
        st.bar_chart(new_data, x="Optimization", y="Total 1 qubit gate")

        st.markdown('## ' + circuit + " - Metric: Total 2 qubit gate")
        new_data = pd.DataFrame({
                    'Optimization': data["opt"],
                    'Total 2 qubit gate': data["qubit_gate_count_2q"],
                })
        st.bar_chart(new_data, x="Optimization", y="Total 2 qubit gate")

        st.markdown('## ' + circuit + " - Metric: Circuit depth")
        new_data = pd.DataFrame({
                    'Optimization': data["opt"],
                    'Circuit depth': data["circuit_depth"],
                })
        st.bar_chart(new_data, x="Optimization", y="Circuit depth")

        st.markdown('## ' + circuit + " - Metric: Circuit cost")
        new_data = pd.DataFrame({
                    'Optimization': data["opt"],
                    'Circuit cost': data["circuit_cost"],
                })
        st.bar_chart(new_data, x="Optimization", y="Circuit cost")

        # st.markdown('## ' + circuit + " - Metric: Execution time")
        # new_data = pd.DataFrame({
        #             'Optimization': data["opt"],
        #             'Execution time': data["execution_time"],
        #         })
        # st.bar_chart(new_data, x="Optimization", y="Execution time")


        # # Grouped Chart
        # metric_table = pd.melt(data, id_vars=['opt'], value_vars=success_rate)

        # chart = alt.Chart(metric_table, title=circuit + " - Success Rate").mark_bar(
        #     opacity=1,
        #     ).encode(
        #     column = alt.Column('opt', spacing = 6, header = alt.Header(labelOrient = "bottom", labelAngle=-90, labelPadding=120)),
        #     x =alt.X('variable', sort = success_rate,  axis=None),
        #     y =alt.Y('value:Q'),
        #     color= alt.Color('variable')
        # ).configure_view(stroke='transparent')

        # st.altair_chart(chart)

    cursor.close()
    conn.close()

def image(src_as_string, **style):
    return img(src=src_as_string, style=styles(**style))

def link(link, text, **style):
    return a(_href=link, _target="_blank", style=styles(**style))(text)


def layout(*args):

    style = """
    <style>
      # MainMenu {visibility: hidden;}
      footer {visibility: hidden;}
    </style>
    """

    style_div = styles(
        left=0,
        bottom=0,
        margin=px(0, 0, 0, 0),
        width=percent(100),
        text_align="center",
        height="60px",
        opacity=0.6
    )

    style_hr = styles(
    )

    body = p()
    foot = div(style=style_div)(hr(style=style_hr), body)

    st.markdown(style, unsafe_allow_html=True)

    for arg in args:
        if isinstance(arg, str):
            body(arg)
        elif isinstance(arg, HtmlElement):
            body(arg)

    st.markdown(str(foot), unsafe_allow_html=True)

def footer():
    myargs = [
        link("https://equip-quantera.github.io/website/", image('https://i.imgur.com/8Rx0Anl.png',
        	width=px(950), height=px(50), margin= "0em")),
    ]
    layout(*myargs)

if __name__ == "__main__":
    footer()