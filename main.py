# -*- coding: utf-8 -*-
import sys
from json import load

try:
    import configparser
    from urllib.request import urlretrieve
except Exception as excp:
    exit("Couldn't import the standard library. Are you running Python 3?")

from PyQt4 import QtGui, QtCore

from src.utils import LinodeApi
from ui import design


config = configparser.ConfigParser()
config.read('config.cfg')

CHECK_IP_MINUTES = config.getint('Settings', 'minutes') * 60
URL_GET_IP = config.get('Settings', 'ipurl')
KEY = config.get('Linode', 'key')
DOMAIN = config.get('Linode', 'domain')
RECORD = config.get('Linode', 'record')


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

