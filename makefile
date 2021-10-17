install_dependencies_ubuntu:
	sudo apt install python3 python3-tkinter python3-feedparser python3-feedgenerator

install:
	cp ./news.py /usr/local/bin/news
	chmod +x /usr/local/bin/news

	-rm -rf /usr/local/lib/news
	cp -r ./news /usr/local/lib/news
