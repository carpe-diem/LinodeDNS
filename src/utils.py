# -*- coding: utf-8 -*-
from json import load

try:
    from urllib.request import urlretrieve
except Exception as excp:
    exit("Couldn't import the standard library. Are you running Python 3?")


API_URL = "https://api.linode.com/api/?api_key={0}&resultFormat=JSON"
API_BASE ="https://api.linode.com/?api_key={key}&api_action={action}&{values}"
API_ACTION_DOMAINS_LIST = "domain.list"
API_ACTION_RESOURCE_LIST = "domain.resource.list"
API_ACTION_RESOURCE_UPDATE = "domain.resource.update"


class LinodeApi(object):

    def __init__(self, ip, key, domain, record):
        self.ip = ip
        self.key=key
        self.domain = domain
        self.record = record

    def __action_url(self, action, values):
        return API_BASE.format(key=self.key, action=action, values=values)

    def __get_data(self, url):
        file, headers = urlretrieve(url)
        json = load(open(file), encoding="utf-8")

        if len(json["ERRORARRAY"]) > 0:
            err = json["ERRORARRAY"][0]
            raise Exception("Error {0}: {1}".format(int(err["ERRORCODE"]),
                err["ERRORMESSAGE"]))
        return load(open(file), encoding="utf-8")

    def __get_domain_id(self):
        url = self.__action_url(API_ACTION_DOMAINS_LIST, '')
        data = self.__get_data(url)

        domain_id = None
        for domain in data['DATA']:
            if self.domain in domain['DOMAIN']:
                domain_id = domain['DOMAINID']

        return domain_id

    def __get_resource_id(self, domain_id):
        domain = "DomainID={d}".format(d=domain_id)
        url = self.__action_url(API_ACTION_RESOURCE_LIST, domain)
        data = self.__get_data(url)

        resource_id = None
        target = None
        for resource in data['DATA']:
            if self.record in resource['NAME']:
                resource_id = resource['RESOURCEID']
                target = resource['TARGET']

        return resource_id, target

    def __update(self, domain_id, resource_id):
        values = "DomainID={d}&ResourceID={r}&Target={t}".format(
            d=domain_id, r=resource_id, t=self.ip)

        url = self.__action_url(API_ACTION_RESOURCE_UPDATE, values)
        data = self.__get_data(url)

        if len(data['ERRORARRAY']) > 0:
            return data['ERRORARRAY']
        else:
            return True

    def send(self):
        try:
            domain_id = self.__get_domain_id()
            if not domain_id:
                return "Bad domain, Please check and test again."

            resource_id, target = self.__get_resource_id(domain_id)
            if not resource_id:
                return "Bad A record, Please check and test again."

            if target == self.ip:
                res = "IP in Linode is ok: {ip}".format(ip=target)
            else:
                res = self.__update(domain_id, resource_id)
                if res is True:
                    res = "IP updated: {old} to {new}".format(
                        old=target, new=self.ip)

        except Exception as excp:
            return "FAIL {0}: {1}".format(type(excp).__name__, excp)

        else:
            return res


