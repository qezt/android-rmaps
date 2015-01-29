# coding: utf8
#wsgiserve_cp2 -t 60 -h 127.0.0.1 -p 12346 > /dev/null

uwsgi --http :12346 -p 5 -T --threads 20 --wsgi-file wsgi_handler.py > /dev/null 2>&1


