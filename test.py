import inspect

def get_calling_function_name(test = None):
    # Get the calling frame (frame of the caller)
    caller_frame = inspect.currentframe().f_back
    
    # Get the name of the calling function
    calling_function_name = caller_frame.f_code.co_name

    # Get the local variables (parameters) of the calling function
    calling_function_locals = caller_frame.f_locals

    return calling_function_name

def example_function(param1, param2, param3):
    # Call get_calling_function_name from within another function
    caller_name = get_calling_function_name("Test")

    print(f"The calling function is {caller_name}")

# Call the example function
example_function(1,4,3)
