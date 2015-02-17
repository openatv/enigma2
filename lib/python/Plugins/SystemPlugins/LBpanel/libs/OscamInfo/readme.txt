## Oscam-Info V0.6
## by Unicorn0815

( for English version scroll down please )

Mit diesem Plugin lassen sich diverse Informationen eines Oscam-Servers
anzeigen. Läuft der Server lokal, also auf der Box, auf der auch das
Plugin installiert ist, besteht die Möglichkeit, die Zugansgdaten für
das Webinterface, direkt aus der Datei oscam.conf auszulesen und zu
verwenden. Alternativ können die Zugangsdaten inklusive IP-Adresse und
Port auch von Hand eingegeben werden, was dann auch den Zugriff auf 
externe, also nicht auf derselben Box laufenden Oscam-Server ermöglicht.
(siehe dazu auch weiter unten bei den Konfigurationsoptionen)

Voraussetzungen:

Das Plugin sollte an sich auf jeder Box lauffähig sein, auf der Enigma2
läuft. Erstellt und getestet wurde es allerdings ausschließlich auf
Dreamboxen mit aktuellem Original-Image.
Da das Plugin auf die XML-API der Oscam zugreift, die z.T. noch weiter
ausgebaut wird, ist zu empfehlen, eine möglichst aktuelle Oscam-Version
zu benutzen, da das Plugin ansonsten nicht alle oder im Extremfall gar keine
Informationen von der Oscam beziehen kann. 
Ab der Oscam-Version 1.00-unstable_svn build #4273 stehen alle zur Zeit
im Plugin vorhandenen Funktionen zur Verfügung. Bei der Verwendung
von früheren Oscam-Versionen kann es zu Fehlfunktionen und/oder Greenscreens
kommen.


Nach dem Start erscheint zunächst das Hauptmenü:

[rot]	/tmp/ecm.info anzeigen
	-> selbstredend ;)
[grün]	Clients anzeigen		
	-> zeigt Infos über die Clients (type = c)
[gelb]	Reader/Proxies anzeigen	
	-> zeigt Server Infos (type = r und type = p)
[blau]	Log anzeigen			
	-> zeigt die aktuellsten Zeilen aus dem Log
[1]	Karteninfos (CCcam-Server)	
	-> zeigt eine Übersicht über von CCcam-Servern
	bezogenen Karten.
[2]	ECM-Statistik
	-> zeigt eine ECM-Statistik eines wählbaren Servers an
[3]	Einstellungen			
	-> Konfiguration
[4]	Readme anzeigen
	-> zeigt diesen Text hier an

Weitere Erläuterungen:

Auf den Seiten "Clients anzeigen" und "Reader/Proxies anzeigen" werden zur
Anzeige verschiedene Farben verwendet. Clients mit dem Status "OK" bzw 
Reader/Proxies mit dem Status "CONNECTED" oder "CARDOK" werden grün dargestellt,
Reader mit Status "NEEDINIT" gelb und Clients bzw Reader mit Status "OFF" oder
"ERROR" in rot.

Auf der Seite "Log anzeigen" hat sich im Gegensatz zu vorigen Versionen lediglich
geändert, dass die Ausgabe nun nicht mehr umgekehrt erfolgt. Die Zeilen werden also
in derselben Reihenfolge ausgegeben, wie sie aus der XML-API ausgelesen werden.

Befindet man sich in der Ansicht "Clients", "Server" oder "Log", kann direkt mit
den Farbtasten zu einer anderen Ansicht umgeschaltet werden. Dabei entsprechen
die Farbtasten derselben Belegung, wie im Hauptmenü.
Zurück ins Hauptmenü gelangt man mit der Exit-Taste.

Die Karteninfos zu den CCcam-Readern geben eine Übersicht über die von einem
CCcam-Server bezogenen Karten. Steht nur ein CCcam-Server zur Verfügung, werden
die Daten direkt angezeigt. Bei mehreren erscheint zunächst eine Auswahlbox, in
welcher der gewünschte Server ausgewählt werden muss.
Angezeigt werden CAID, Verschlüsselungssystem, Zahl der Karten auf Hop 1,2,3,4,5,
die Gesamtzahl der Karten und der Reshare-Wert. Ausserdem eine Zusammenfassung der
Provider, welche mit dieser Karte entschlüsselt werden können.
In der Titelzeile findet sich der Name des Servers, die Gesamtzahl der Karten dieses
Servers und die Host-Adresse.

Die ECM-Statistik zeigt eine Zusammenfassung der ECM-Anfragen bezogen auf die verfügbaren
Server. Zunächst erscheint eine Auswahlbox, in der ein Server gezielt ausgewählt werden
kann. Alternativ kann auch der Punkt "Alle" gewählt werden.
Angezeigt werden dann der Server-Name, CAID, Kanalname, ECM-Durchschnitt, letzte ECM-Zeit,
Status (found/not found), Zeit der letzten Anfrage und die Gesamtzahl der ECMs.
In der Titelzeile steht die vorher gewählte Option, also "Alle Server" oder der gewählte
Servername.
Bitte denkt daran, dass diese Liste abhängig von der Oscam-Konfiguration und Laufzeit der
Oscam ziemlich lang werden kann ;)

In den "Einstellungen" kann gewählt werden, ob die Benutzerdaten aus der oscam.conf gelesen
werden sollen oder nicht. Wenn ja, kann noch gewählt werden, ob die Client/Server bzw Log-
Ansicht automatisch aktualisiert werden soll oder nicht. Wenn ja, ist noch das 
Aktualisierungs-Intervall in Sekunden einstellbar (im Bereich 10 - 60 Sekunden, 
Default ist 10), welches die Abstände angibt, in welchen die Anzeigen für Clients, 
Reader/Proxies und Log aktualisiert werden. Wird eingestellt, dass die Benutzerdaten NICHT 
aus der oscam.conf gelesen werden sollen, gibt es noch die Zeilen Benutzername, 
Passwort, IP-Adresse und Port für den Zugriff auf das Webinterface der Oscam.

Alle Ansichten (Client, Server, Log, Karteninfos und ECM-Statistik) können mit der OK-Taste
manuell aktualisiert werden, egal ob automatische Aktualisierung eingeschaltet ist oder
nicht.

Bei Fragen, Anregungen usw bin ich im Keywelt-Board zu finden ( http://www.keywelt-board.com ).

Gruss
Unicorn0815

--------------------------------------------------------------------------------

This plugin shows several information about a running Oscam-server. If the server runs
on the local box ( the box this plugin is installed on ), it is possible to get the
username and password for accessing the oscam-webinterface directly from the file oscam.conf.
If this behaviour is not wanted, or there is no oscam running on this box, you can enter
the required data manually to access external servers.

Requirements:
	
The Plugin should be working on any box running Enigma2, though it is made and tested by
me only on Dreamboxes with an original image.
As the plugin accesses the XML-API of oscam, which is still in development, I recommend to
use one of the latest versions, because with older versions the plugin may not get all,
or even no information from oscam.
This version of OscamInfo (V 0.6) has been tested starting with 
oscam 1.00-unstable_svn build #4273. Using older version may lead to green screens or
just not getting the desired information.


When you start the plugin, the main menu looks as follows:
	
[red]	Show /tmp/ecm.info
	-> says exactly what it does ;)
[green]	Show Clients
[yellow] Show Readers/Proxies
[blue]	Show log
	-> shows the latest entries in the log
[1]	Card infos (CCcam Reader)
	-> shows a overview about received cards of a CCcam-server
[2]	ECM Statistics
	-> gives the ecm statistics of a selected server
[3]	Setup
[4]	Show Readme
	-> This text...
	
When "Show Clients" or "Show Readers/Proxies" is selected, the results are shown
in different colours. Clients with status "OK" and Readers/Proxies with status
"CONNECTED" or "CARDOK" are shown in green, readers with status "NEEDINIT" are shown
in yellow and clients or readers with status "OFF" or "ERROR" are shown in red.

When displaying the log, nothing changed compared to earlier versions of this plugin,
except for sorting the result. In this version the lines are shown as they are
read out from the webinterface and no longer in reverse order.

When in client-, server or log view the displayed source can be changed using the
colour buttons ( green -> clients, yellow -> servers, blue -> log ).

The card-info screen for CCcam-readers gives an overview about the received cards.
If just one cccam-server is configured, its data will be shown directly. If there
is more than one server, a choicebox asks for which server should be shown.
Available information is CAID, cryptsystem, number of cards on hop 1,2,3,4,5,
total number of cards and the reshare value. Additionally a summary of providers
which can be decrypted by this card.

The ecm-statistics give a summary about ecm request to available servers. When this
item is selected, the desired server can be selected in a choicebox.
Available information is the name of the server, CAID, channel name, average ecm-time,
last ecm time, status (found/not found), time of last request and total sum of ecms.

In the setup screen you can choose, if username and password should be read from
oscam.conf or not. If set to yes, there is only one more configurable item, which is
"automatically update client/server view?". If this is set to "Yes", the interval can
be set between 10 and 600 seconds. This means, that the data in client, server or log
view is updated every x seconds, depending on this setting.
If "read userdata from oscam.conf" is set to "No", you can enter username, password,
ip address and port manually.

All views (client, server, log, cardinfos or ecm statistics) can be updated manually by
pressing OK on the remote control, no matter if automatic update is on or off in the
setup.

For questions, suggestions and so on you can reach me here: 
http://www.keywelt-board.com

Have fun

Unicorn0815
