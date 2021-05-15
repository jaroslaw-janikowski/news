install_dependencies_ubuntu:
	sudo apt install python3 python3-tkinter python3-feedparser

install:
	mkdir -p /usr/share/icons/news

	cp ./news.py /usr/local/bin/news
	chmod +x /usr/local/bin/news

	cp ./res/icons/folder.png /usr/share/icons/news/folder.png
	cp ./res/icons/rss.png /usr/share/icons/news/rss.png
	cp ./res/icons/youtube.png /usr/share/icons/news/youtube.png
	cp ./res/icons/twitch.png /usr/share/icons/news/twitch.png
