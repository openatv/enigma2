Anleitung zum erstellen eine eigene Fastscan's

own_scan.txt im xml Ordner
in der own_scan.txt müssen die Sender in der Schreibweise reingeschrieben werden wie sie von E2 gefunden werden 
heißt wie sie auch in Dreamedit oder anderen Settingseditoren abzulesen sind.
Die Reihenfolge die man hier erstellt ist auch diese wie sie später im Bouquet zu finden sind.


own_scan.xml im xml Ordner
in die own_scan.xml kommen die Infos über den/die Transponder auf denen die Sender gesucht werden müssen für jeden Transponder muss eine eigene Zeile gemacht werden.
Diese ist folgendermassen aufgebaut:

orbpos ist die Satelliten Position für Ost kann man einfach die Gradzahl ohne Komma in den "" reinschreiben also 19.2 Ost ist dann 192, bei West ist es da etwas anders,
man muss die Zahl ohne Komma von 3600 abziehen und das Ergebnis ist dann die orbpos, bei 0,8West z.b. ist es dann 3592.

Frequency,  symbolrate, fec, pol, system und modulation sollten klar sein, das sind die Transponderdaten die man z.b. bei King oF Sat findet, 
wobei man bei System alles zusammen, groß und ohne Sonderzeichen schreiben muss.

Wenn das alles Fertig ist einfach den Punkt Own_Scan im Fastscan Menu nutzen und man bekommt sein eigenen Fav so wie man ihn haben will.
