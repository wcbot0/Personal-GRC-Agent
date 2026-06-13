# Intentionally vulnerable code for repo-security-review evals — NOT production code.
import os
import pickle
import subprocess

DEBUG = True
password = "super_secret_key_1234567890"

def run_query(user_input):
    cursor.execute(f"SELECT * FROM users WHERE name = '{user_input}'")

def unsafe_eval(code):
    return eval(code)

def load_data(blob):
    return pickle.loads(blob)

def run_cmd(cmd):
    subprocess.call(f"echo {cmd}", shell=True)
