# -*- coding: utf-8 -*-
import sys
from json import load

try:
    import configparser
    from urllib.parse import urlencode
    from urllib.request import urlretrieve
except Exception as excp:
    exit("Couldn't import the standard library. Are you running Python 3?")

from PyQt4 import QtGui, QtCore

from ui import design


config = configparser.ConfigParser()
config.read('config.cfg')

CHECK_IP_MINUTES = config.getint('Settings', 'minutes') * 60
URL_GET_IP = config.get('Settings', 'ipurl')
KEY = config.get('Linode', 'key')
DOMAIN = config.get('Linode', 'domain')
RECORD = config.get('Linode', 'record')


API_URL = "https://api.linode.com/api/?api_key={0}&resultFormat=JSON"
API_BASE ="https://api.linode.com/?api_key={key}&api_action={action}&{values}"
API_ACTION_DOMAINS_LIST = "domain.list"
API_ACTION_RESOURCE_LIST = "domain.resource.list"
API_ACTION_RESOURCE_UPDATE = "domain.resource.update"




class GetIP(QtCore.QThread):

    def __init__(self):
        QtCore.QThread.__init__(self)

    def __del__(self):
        self.wait()

    def __get_ip(self):
        file, headers = urlretrieve(URL_GET_IP)
        ip = open(file).read()
        return ip

    def run(self):
        while True:
            ip = self.__get_ip()
            self.emit(QtCore.SIGNAL('add_ip(QString)'), ip)
            self.sleep(CHECK_IP_MINUTES)


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


class LinodeAPIApp(QtGui.QMainWindow, design.Ui_MainWindow):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.setupUi(self)
        self.initUi()

        self.icon = QtGui.QSystemTrayIcon()
        self.icon.setIcon(QtGui.QIcon('images/logo.png') )
        self.icon.show()

        QtCore.QObject.connect(
            self.btnsend, QtCore.SIGNAL("clicked()"),
            self.send_configuration)

        QtCore.QObject.connect(
            self.btnsave, QtCore.SIGNAL("clicked()"),
            self.save_configuration)

        QtCore.QObject.connect(
            self.btnquit, QtCore.SIGNAL("clicked()"),
            self.quit)

        QtCore.QObject.connect(self.icon,
            QtCore.SIGNAL("activated(QSystemTrayIcon::ActivationReason)"),
            self.__icon_activated)

    def quit(self):
        self.hide()

    def __icon_activated(self, reason):
        if reason == QtGui.QSystemTrayIcon.DoubleClick:
            self.show()

    def initUi(self):
        # Values from config file
        self.txtapikey.setText(KEY)
        self.txtdomain.setText(DOMAIN)
        self.txtrecord.setText(RECORD)

        # Public IP section
        self.get_ip_thread = GetIP()
        self.connect(self.get_ip_thread, QtCore.SIGNAL("add_ip(QString)"),
                self.add_ip)
        self.get_ip_thread.start()

    def add_ip(self, ip):
        self.lblcheckip.setText(ip)
        self.ip = ip
        self.btnsend.setEnabled(True)
        last_ip = config.get('Linode', 'lastip')
        if last_ip != self.ip:
            config.set('Linode', 'lastip', self.ip)
            with open('config.cfg', 'w') as configfile:
                config.write(configfile)
            self.send_configuration()

    def send_configuration(self):
        key = self.txtapikey.text()
        domain = self.txtdomain.text()
        record = self.txtrecord.text()

        if not key:
            msg = "Key value is empty"
        if not domain:
            msg = "Domain value is empty"
        if not record:
            msg = "Resource value is empty"
        else:
            self.lblresponse.setText('Waiting...')
            api = LinodeApi(self.ip, key, domain, record)
            msg = api.send()

        self.lblresponse.setText(msg)

    def save_configuration(self):
        key = self.txtapikey.text()
        domain = self.txtdomain.text()
        record = self.txtrecord.text()

        config.set('Linode', 'key', key)
        config.set('Linode', 'domain', domain)
        config.set('Linode', 'record', record)
        with open('config.cfg', 'w') as configfile:
            config.write(configfile)

        self.quit()


def main():
    app = QtGui.QApplication(sys.argv)
    form = LinodeAPIApp()
    form.show()
    app.exec_()


if __name__ == '__main__':
    main()

