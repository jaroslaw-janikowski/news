install_dependencies_ubuntu:
	sudo apt install python3 python3-tkinter python3-feedparser python3-feedgenerator

install:
	mkdir -p /usr/share/icons/news

	cp ./news.py /usr/local/bin/news
	chmod +x /usr/local/bin/news

	mkdir -p /usr/lib/python3/dist-packages/bpsnews/scripts
	cp ./bpsnews/__init__.py /usr/lib/python3/dist-packages/bpsnews/__init__.py
	cp ./bpsnews/scripts/__init__.py /usr/lib/python3/dist-packages/bpsnews/scripts/__init__.py
	cp ./bpsnews/scripts/zbiampl.py /usr/lib/python3/dist-packages/bpsnews/scripts/zbiampl.py
	cp ./bpsnews/scripts/tibiacom.py /usr/lib/python3/dist-packages/bpsnews/scripts/tibiacom.py

	cp ./res/icons/folder.png /usr/share/icons/news/folder.png
	cp ./res/icons/rss.png /usr/share/icons/news/rss.png
	cp ./res/icons/youtube.png /usr/share/icons/news/youtube.png
	cp ./res/icons/twitch.png /usr/share/icons/news/twitch.png
	cp ./res/icons/like.png /usr/share/icons/news/like.png
