import json

def read_file(file_path):
    try:
        with open(file_path, "r") as file:
            # Read the contents of the file and store them in the variable
            file_contents = file.read()

    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    return file_contents

def convert_to_json(dictiontary):
    return json.dumps(dictiontary, indent = 0) 