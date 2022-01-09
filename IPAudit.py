#!/usr/bin/python3
import dns.reversename

try:
    import argparse
    import concurrent.futures
    import config
    import json
    import re
    import requests
    import socket
    import time
    from billing_api.billingauth import billing_user, billing_token
    from dns import reversename, resolver
    from netaddr import IPNetwork
except (ModuleNotFoundError, ImportError) as module:
    quit(f'The following module needs to be installed:\n {module}\n Use "pip install $MODULE" then try again.\n')


class Data:
    def __init__(self):
        """Set the variables."""
        self.uuid = self.host = self.account = None
        self.url = ''
        self.params = ''
        self.types = config.excluded_types
        self.subaccount_list = []
        self.dictionary = {}
        self.dictionary_keys = ['accnt', 'activeStatus', 'domain', 'type', 'uniq_id']

    def validate(self, string):
        """Check if UUID, Host name, or Account Number"""
        regex1 = re.compile('^[0-9]+$')  # Check if account number 1 to 6 numbers.
        regex2 = re.compile('^[0-9a-zA-Z]{6}$')  # Check if UUID (6 characters).
        regex3 = re.compile(r'^[a-zA-Z0-9.-]+$')  # Verify no invalid characters
        regex4 = re.compile(r'^(?!\.).+(?<=\.).+\..+(?!\.)$')  # Check if Hostname. Has at least 2 periods and does
        # not begin with or end with a period.
        if regex1.search(string) is not None:
            print(f'Performing Account Search: {string}')
            self.account = string
            self.account_search()
        elif regex2.search(string) is not None:
            print(f'Performing UUID Search: {string}')
            self.uuid_search(string)
        elif regex3.search(string) and regex4.search(string) is not None:
            print(f'Performing Hostname Search: {string}')
            self.host = string
            self.host_search()
        else:
            print(f'regex1 = {regex1.search(string)}\nregex2 = {regex2.search(string)}'
                  f'\nregex3 = {regex3.search(string)}\nregex4 = {regex4.search(string)}')
            quit(f'{string}\n Invalid Search.\n Please provide a valid UUID, Hostname, or Account Number.\n')
        return self.dictionary

    def get_data(self):
        """Grab data from billing"""
        req = {'params': self.params}
        send = requests.post(self.url, auth=(billing_user, billing_token), data=json.dumps(req))
        send2 = send.json()
        return send2

    def get_rdns(self, address):
        """Get domain of PTR record then remove tailing period of the name"""
        try:
            data = resolver.resolve_address(address)[0]
            if str(data)[-1] == '.':
                data = str(data)[:-1]
        except (resolver.NXDOMAIN, resolver.NoAnswer):
            data = ''

        return data

    def account_search(self):
        """Grab list of UUIDs on a given account number."""
        self.url = config.api_1
        self.params = {'accnt': self.account, 'page_size': 10000}
        data = self.get_data()
        for k in data['items']:
            if k['type'] not in self.types:
                self.subaccount_list.append(k['uniq_id'])
        print(f'Pulling data for {len(self.subaccount_list)} subaccounts.')
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.uuid_search, self.subaccount_list)
        return

    def uuid_search(self, uuid):
        """Grab initial data for a specific UUID."""
        self.url = config.api_2
        self.params = {'uniq_id': uuid}
        data = self.get_data()
        d = self.dictionary
        n = uuid
        d[n] = {}
        for key, value in data.items():
            if key in self.dictionary_keys:
                d[n].update({key: value})
        self.parse_ip_addresses(uuid)
        self.parse_ip_billing(uuid)
        return

    def parse_ip_addresses(self, uuid):
        """Grab IP Billing data for a given UUID."""
        self.url = config.api_3
        self.params = {
            'uniq_id': uuid,
            'page_size': 10000
        }
        data = self.get_data()
        d = self.dictionary
        ip_list = 'ip_list'
        n = uuid
        list_ips = {}
        d[n].update({ip_list: {}})
        for key in data['items']:
            vlan = key['vlan']
            netrange = key['network']
            if ':' not in netrange:
                for ip in IPNetwork(str(netrange)):
                    list_ips.update({str(ip): vlan})
        list_ips_sorted = sorted(list_ips.items(), key=lambda item: socket.inet_aton(item[0]))
        count = 1
        for ip, vlan in list_ips_sorted:
            i = 'ip' + str(count).zfill(3)
            try:
                d[n][ip_list][i].update({'address': ip, 'vlan': vlan, 'rdns': self.get_rdns(ip)})
            except (AttributeError, KeyError):
                d[n][ip_list][i] = {'address': ip, 'vlan': vlan, 'rdns': self.get_rdns(ip)}
            finally:
                count += 1
        d[n].update({'ip_count': len(list_ips)})
        # print(json.dumps(d, sort_keys=True, indent=4))
        return

    def parse_ip_billing(self, uuid):
        """Grab a list of IP Addresses assigned for a given UUID."""
        self.url = config.api_4
        if not uuid:
            uuid = self.uuid
        self.params = {'uniq_id': uuid}
        data = self.get_data()
        d = self.dictionary
        n = uuid
        try:
            nip = data['netblock_ips']
            ip_change = data['ip_change']
            ccost = data['current']['total_price']
            pcost = int(float(data['proposed']['total_price']))
            features = data['current']['features']
        except KeyError:
            if data['error']:
                nip = ip_change = ccost = pcost = features = 'ERROR'
        finally:
            d[n]['ipdetails'] = {}
            d[n]['ipdetails'].update({'netblock_ips': nip})
            d[n]['ipdetails'].update({'ip_change': ip_change})
            d[n]['ipdetails'].update({'current_cost': ccost})
            d[n]['ipdetails'].update({'proposed_cost': pcost})
            d[n]['ipdetails'].update({'features': features})
        return

    def host_search(self):
        """Find the UUID of the host and send it to uuid_search()"""
        self.url = config.api_5
        self.params = {'domain': self.host}
        data = self.get_data()
        if not data['items']:
            quit(f'\n Unable to find host: {self.host}\n')
        else:
            for k in data['items']:
                if k['type'] not in self.types:
                    self.subaccount_list.append(k['uniq_id'])
        if not self.subaccount_list:
            quit(f'\n {self.host} subaccount found does not appear to be netblock compatible.\n')
        elif len(self.subaccount_list) > 1:
            quit(f'\n There appears to be multiple devices with the hostname: {self.host}\n '
                 f'Please rerun with the correct UUID: {self.subaccount_list}')
        else:
            self.uuid_search(self.subaccount_list[0])
        return


def output(string, file=None):
    key_list = string.keys()
    account = string[list(key_list)[0]]['accnt']
    message = f'\nAccount Number:\t\t {account}'
    for nested in string:
        hostname = string[nested]['domain']
        uuid = string[nested]['uniq_id']
        host_type = string[nested]['type']
        current_billed = string[nested]['ipdetails']['current_cost']
        if current_billed != 'ERROR':
            current_billed = "${:,.2f}".format(current_billed)
        net_ips = string[nested]['ip_count']
        list_ip = string[nested]['ip_list']
        message += (
            f'\n\nHostname:\t\t {hostname} - {uuid} \nHost Type:\t\t {host_type}'
            f'\nIP Addresses Billing:\t {current_billed} \nNetblocked Addresses:\t [ {net_ips} ]'
            f'\n\tVLAN\t\tIP Address(es)\t\trDNS')
        for ip_nest in list_ip:
            vlan = list_ip[ip_nest]['vlan']
            address = list_ip[ip_nest]['address']
            rdns = list_ip[ip_nest]['rdns']
            message += f'\n\t{vlan}\t\t{address}\t\t{rdns}'
    print(message)
    if file:
        file1 = open(file, 'w')
        file1.write(message)
        file1.close()
        print('Output sent to: ' + file1.name)


def main():
    start = time.perf_counter()
    parser = argparse.ArgumentParser(description="Script to lookup IP Address usage for a host or account.",
                                     epilog="Provide UUID, Hostname, or account number to search.")
    parser.add_argument('-f', '--file', metavar='<FILE>', help='Output to a file.', dest='write_file')
    parser.add_argument("string", help="UUID, Hostname, or Account number")
    args = parser.parse_args()
    v = Data()
    output(v.validate(args.string), args.write_file)
    finish = time.perf_counter()
    print(f'\nReport completed in {round(finish - start, 2)} second(s)')


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        quit('')
