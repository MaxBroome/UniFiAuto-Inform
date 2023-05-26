import socket
import subprocess
import re
import paramiko
import time
from threading import Thread, Lock
from time import perf_counter
from colorama import *

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

init(convert=True)

print(f"{bcolors.UNDERLINE}Searching for Ubiquiti Devices...{bcolors.ENDC}")

BASE_IP = "%s.%i"
PORT = 8080

class Threader:
    def __init__(self, threads=30):
        self.thread_lock = Lock()
        self.functions_lock = Lock()
        self.functions = []
        self.threads = []
        self.nthreads = threads
        self.running = True

    def stop(self) -> None:
        self.running = False

    def append(self, function, *args) -> None:
        self.functions.append((function, args))

    def start(self) -> None:
        for i in range(self.nthreads):
            thread = Thread(target=self.worker, daemon=True)
            thread._args = (thread, )
            self.threads.append(thread)
            thread.start()

    def join(self) -> None:
        for thread in self.threads:
            thread.join()

    def worker(self, thread:Thread) -> None:
        while self.running and (len(self.functions) > 0):
            with self.functions_lock:
                function, args = self.functions.pop(0)
            function(*args)

        with self.thread_lock:
            self.threads.remove(thread)

start = perf_counter()
socket.setdefaulttimeout(1.0)

def connect(hostname, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex((hostname, port))

def get_gateway_octets():
    result = subprocess.run('ipconfig', capture_output=True, text=True)
    output = result.stdout

    gateways = re.findall(r'IPv4 Address[^:]+:\s+(\d+\.\d+\.\d+)\.\d+', output)
    return gateways

# Retrieve gateways
gateways = get_gateway_octets()

total_ips = len(gateways) * 255
n_threads = min(total_ips, 30)

threader = Threader(n_threads)
for gateway in gateways:
    for i in range(255):
        threader.append(connect, BASE_IP % (gateway, i), PORT)
        if len(threader.functions) >= n_threads:
            threader.start()
            threader.join()

threader.start()
threader.join()

end = perf_counter()

mac_prefixes = [
    "00-15-6D", "00-27-22", "00-50-C2", "04-18-D6", "18-E8-29", "24-5A-4C",
    "24-A4-3C", "28-70-4E", "44-D9-E7", "60-22-32", "68-72-51", "68-D7-9A",
    "70-A7-41", "74-83-C2", "74-AC-B9", "78-45-58", "78-8A-20", "80-2A-A8",
    "94-2A-6F", "9C-05-D6", "AC-8B-A9", "B4-FB-E4", "D0-21-F9", "D8-B3-70",
    "DC-9F-DB", "E0-63-DA", "E4-38-83", "F0-9F-C2", "F4-92-BF", "F4-E2-C6",
    "FC-EC-DA"
]

arp_output = subprocess.check_output("arp -a").decode()

ubiquiti_devices = []

for line in arp_output.splitlines():
    for prefix in mac_prefixes:
        if re.search(prefix, line, re.I):
            ip_match = re.search(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", line)
            if ip_match:
                ip = ip_match.group(0)
                mac = re.search(r"([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}", line).group(0)
                mac = re.sub(r"\s+dynamic|\s", "", mac)
                ubiquiti_devices.append({
                    "IPAddress": ip,
                    "MACAddress": mac
                })
                break

if len(ubiquiti_devices) == 0:
    print(f"{bcolors.WARNING}No Ubiquiti devices found.){bcolors.ENDC}")
else:
    print(f"{bcolors.OKGREEN}Found {len(ubiquiti_devices)} Ubiquiti Devices!{bcolors.ENDC}")
    for device in ubiquiti_devices:
        ip = device["IPAddress"]
        mac = device["MACAddress"]
        print(f"{bcolors.OKBLUE}IP Address: {ip}, MAC Address: {mac}{bcolors.ENDC}")

run_set_inform = input("Do you want to run a set-inform command on all devices? (y/n): ")

if run_set_inform.lower() == "y":
    use_custom_credentials = input(f"{bcolors.WARNING}Do you want to use custom SSH credentials? (y/n): {bcolors.ENDC}")

    if use_custom_credentials.lower() == "y":
        username = input("Enter the SSH username: ")
        password = input("Enter the SSH password: ")
    else:
        username = "ubnt"
        password = "ubnt"

    controller_ip = input(f"{bcolors.HEADER}Enter the IP address or FQDN of your UniFi controller: {bcolors.ENDC}")

    for device in ubiquiti_devices:
        ip = device["IPAddress"]

        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(ip, username=username, password=password)

            time.sleep(.5)  # Add a delay of half a second

            command = f"/usr/bin/mca-cli-op set-inform http://{controller_ip}:8080/inform"
            stdin, stdout, stderr = ssh_client.exec_command(command)

            success_output = "Adoption request sent to"
            if success_output in stdout.read().decode():
                print(f"{bcolors.OKGREEN}Set-inform command sent successfully to {ip}{bcolors.ENDC}")
            else:
                print(f"{bcolors.FAIL}Failed to send set-inform command to {ip}{bcolors.ENDC}")

            ssh_client.close()
        except Exception as e:
            print(f"{bcolors.FAIL}Error connecting to {ip}: {str(e)}{bcolors.ENDC}")
print(f"{bcolors.BOLD}Thank you for using my script!{bcolors.ENDC}")
print("With <3  - MaxBroome on GitHub")
time.sleep(3)
print("Exiting Now! Bye!")
time.sleep(5)
