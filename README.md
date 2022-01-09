## Server IP Audit

This script will give the number of IP addresses netblocked, the cost, and list of IPs with respective VLAN. The goal with this script is to help reduce the time it takes to audit a server when a customer request for additional addresses.

Currently this script built for Pyt3.x and will fail with Python 2.x.

---

### Example of install with python virtual environment:

```
mkdir ~/script_location/
cd ~/script_location/
git init
git remote add origin git@github.com:williamjv/server_IP_info.git
git pull origin master
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Python Virtual Environment Examples:

To enter into the virtual environment:
```
cd ~/script_location/
source venv/bin/activate
```

To exit the virtual environment:
```
deactivate
```

---

### Example of uses:

1. Host search:
   - `python IPAudit.py host.example.com`
2. UID search:
   - `python IPAudit.py UUID`
3. Account search:
   - `python IPAudit.py 123456`
4. Write to file:
   - `python IPAudit.py 123456 -f file.txt`
5. List options:
   - `python IPAudit.py --help`

---

### Example output:

```
Performing Hostname Search: host.example.com

Account Number:		 123456

Hostname:		 host.example.com - UUID
Host Type:		 Dedi.example
IP Addresses Billing:	 $6.00 
Netblocked Addresses:	 [ 4 ]
	VLAN		IP Address(es)		rDNS
	111		127.0.0.1		loopback.1
	111		127.0.0.2		loopback.2
	111		127.0.0.3		loopback.3
	111		127.0.0.4		loopback.4
Output sent to: file.txt

Report complete.
```
