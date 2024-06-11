import requests
import json
import mysql.connector
import time

mysql_config = {
    'user': 'handy',
    'password': 'handy',
    'host': 'ec2-13-60-50-75.eu-north-1.compute.amazonaws.com',
    'database': 'framework'
}

def send_rest_api_request(url, token):
    response = requests.request(
        "GET",
        url,
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(token)
        },
    )

    return response.json()

def get_qiskit_user_info(token):

    response_json = send_rest_api_request("https://api.quantum-computing.ibm.com/runtime/users/me", token)

    email = response_json["email"]
    plan = response_json["instances"][0]["plan"]

    return email, plan

def get_qiskit_usage_info(token):

    response_json = send_rest_api_request("https://api.quantum-computing.ibm.com/runtime/usage", token)

    print(response_json)

    instance = response_json["byInstance"][0]["instance"]
    quota = response_json["byInstance"][0]["quota"]
    usage = response_json["byInstance"][0]["usage"]
    pendingJobs = response_json["byInstance"][0]["pendingJobs"]
    maxPendingJobs = response_json["byInstance"][0]["maxPendingJobs"]

    return instance, quota, usage, pendingJobs, maxPendingJobs

def update_qiskit_usage_info(token):

    print("Start inserting...")
    print("==================")
    print(token)

    instance, quota, usage, pendingJobs, maxPendingJobs = get_qiskit_usage_info(token)

    email, plan = get_qiskit_user_info(token)

    conn = mysql.connector.connect(**mysql_config)
    cursor = conn.cursor()
    
    # check if the metric is already there, just update
    cursor.execute('SELECT token FROM qiskit_token WHERE token = %s', (token,))
    existing_row = cursor.fetchone()

    # insert to the table
    if not existing_row:
        cursor.execute("""INSERT INTO qiskit_token (token, str_instance, int_quota, int_usage, int_remaining, 
                       int_pending_jobs, int_max_pending_jobs, str_email, str_plan)
                        VALUES (%s, %s, %s, %s, %s, 
                       %s, %s, %s, %s)""",
        (token, instance, quota, usage, quota - usage, 
         pendingJobs, maxPendingJobs, email, plan))

        conn.commit()

        print(token, "has been registered to the database.")
    else:
        cursor.execute("""UPDATE qiskit_token SET str_instance = %s, int_quota = %s, int_usage = %s, 
                       int_remaining = %s, int_pending_jobs = %s, int_max_pending_jobs = %s, str_email = %s, str_plan = %s
                            WHERE token = %s""",
        (instance, quota, usage, 
         quota - usage, pendingJobs, maxPendingJobs, email, plan,
         token))

        conn.commit()
        print(token, " is updated.")
    
    cursor.close()
    conn.close()
    
def get_all_token():
    conn = mysql.connector.connect(**mysql_config)
    cursor = conn.cursor()
    
    cursor.execute('''SELECT token FROM qiskit_token WHERE int_pending_jobs > 0 ''')
    
    results = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return results

def get_new_token():
    conn = mysql.connector.connect(**mysql_config)
    cursor = conn.cursor()
    
    cursor.execute('''SELECT token FROM qiskit_token WHERE str_email IS NULL ''')
    
    results = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return results

results = get_all_token()
for res in results:
    token = res[0]

    update_qiskit_usage_info(token)

    time.sleep(10)

# for new token
results = get_new_token()
for res in results:
    token = res[0]
    update_qiskit_usage_info(token)

    time.sleep(10)
    
