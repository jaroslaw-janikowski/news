install_dependencies_ubuntu:
	sudo apt install python3-gi gobject-introspection gir1.2-gtk-3.0 python3-feedparser

uninstall:
	rm -rf /usr/lib/python3/dist-packages/com/bps/news
	rm -rf /usr/share/icons/news

install: uninstall
	mkdir -p /usr/lib/python3/dist-packages/com/bps/news
	mkdir -p /usr/share/icons/news

	cp ./com/bps/__init__.py /usr/lib/python3/dist-packages/com/bps/__init__.py
	cp ./com/bps/news/__init__.py /usr/lib/python3/dist-packages/com/bps/news/__init__.py
	cp ./com/bps/news/database.py /usr/lib/python3/dist-packages/com/bps/news/database.py
	cp ./com/bps/news/ui.py /usr/lib/python3/dist-packages/com/bps/news/ui.py
	cp ./com/bps/news/updater.py /usr/lib/python3/dist-packages/com/bps/news/updater.py
	cp ./com/bps/news/parentalctrl.py /usr/lib/python3/dist-packages/com/bps/news/parentalctrl.py
	cp ./com/bps/news/resources.py /usr/lib/python3/dist-packages/com/bps/news/resources.py

	cp ./res/icons/folder.png /usr/share/icons/news/folder.png
	cp ./res/icons/rss.png /usr/share/icons/news/rss.png
	cp ./res/icons/youtube.png /usr/share/icons/news/youtube.png

	cp ./main.py /usr/bin/news

	chmod +x /usr/bin/news
