from abc import ABC, abstractmethod
from typing import Dict, List, Type

class BaseWrapper(ABC):
    _optimization_type: str = ""
    pass

# def _save_result_to_db(self, updated_qasm):
#         # Get the calling frame (frame of the caller)
#         caller_frame = inspect.currentframe().f_back
#         # Get the name of the calling function
#         calling_function_name = caller_frame.f_code.co_name
#         # Get the local variables (parameters) of the calling function
#         calling_function_locals = caller_frame.f_locals

#         now_time = datetime.now().strftime("%Y%m%d%H%M%S")

#         detail_id = None
#         job_id = None

#         try:
            
#             p_qiskit_optimization, p_apply_qiskit, p_triq_optimization = None, None, None
#             sabre, mirage, mitiq, p_laura_optimization = None, None, None, None
#             p_calibration_type = None

#             for i in calling_function_locals.keys():
#                 if i != "self" and i != "updated_qasm":
#                     if i == "qiskit_optimization_level":
#                         p_qiskit_optimization = calling_function_locals[i]
#                     elif i == "apply_qiskit":
#                         p_apply_qiskit = calling_function_locals[i]
#                     elif i == "triq_optimization":
#                         p_triq_optimization = calling_function_locals[i]
#                     elif i == "laura_optimization":
#                         p_laura_optimization = calling_function_locals[i]
#                     elif i == "enable_sabre":
#                         sabre = 1 if calling_function_locals[i] == True else 0
#                     elif i == "enable_mirage":
#                         mirage = 1 if calling_function_locals[i] == True else 0
#                     elif i == "calibration_type":
#                         p_calibration_type = calling_function_locals[i]

#             # Connect to the MySQL database
#             conn = mysql.connector.connect(**self.mysql_config)
#             cursor = conn.cursor()
            
#             # insert to detail
#             now_time = datetime.now().strftime("%Y%m%d%H%M%S")
#             sql = '''INSERT INTO result_detail (user_id, header_id, job_id, status, 
#                            qiskit_optimization, apply_qiskit, triq_optimization, calibration_type, sabre, 
#                            mirage, mitiq, laura_optimization, created_datetime) 
#                            VALUES (
#                            %s, %s, %s, %s, 
#                            %s, %s, %s, %s, %s, 
#                            %s, %s, %s, %s)'''
            
#             parms = (self.user_id, self.header_id, job_id, "pending",  
#                          p_qiskit_optimization, p_apply_qiskit, p_triq_optimization, p_calibration_type, sabre,
#                          mirage, mitiq, p_laura_optimization, now_time)
#             cursor.execute(sql, parms)

#             detail_id = cursor.lastrowid

#             # insert to result_updated_qasm
#             cursor.execute('''INSERT INTO result_updated_qasm (detail_id, updated_qasm, qiskit_qasm, qasm_before_decomposed_final) 
#                            VALUES (
#                            %s, %s, %s, %s)''',
#                         (detail_id, updated_qasm, self.qiskit_qasm, self.qasm_before_decomposed_final))

#             conn.commit()
#             cursor.close()
#             conn.close()

#             return detail_id
        
#         except Exception as e:
#             print(f"An error occurred: {str(e)}")